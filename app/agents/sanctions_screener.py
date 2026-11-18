import os

from langchain_anthropic import ChatAnthropic

from app.models.schemas import ComplianceState, SanctionsResult
from app.tools import watchlist
from app.utils.logging import get_logger, mask_sensitive_field

logger = get_logger(__name__)

_PROMPT = """You are a trade finance sanctions compliance analyst.

The following deterministic watchlist checks were run against a trade document. Review the results and produce a structured sanctions assessment.

Document fields screened:
- Buyer: {buyer}
- Seller: {seller}
- Vessel: {vessel_name}
- Country of origin: {country_of_origin}
- Port of loading: {port_of_loading}
- Port of discharge: {port_of_discharge}
- Goods: {goods_description}

Watchlist results:
{hits_summary}

Provide:
- hits: one string per match found (empty list if none)
- is_clear: true only if no watchlist hits were found
- severity: "none" if no hits; otherwise the highest severity among hits ("medium", "high", or "critical")
- confidence: your confidence in this assessment (0.0–1.0)
- summary: a concise finding suitable for a compliance officer
"""


def screen_sanctions(state: ComplianceState) -> dict:
    doc = state.get("document_data")
    if doc is None:
        return {
            "sanctions_result": SanctionsResult(
                hits=[],
                is_clear=False,
                severity="none",
                confidence=0.0,
                summary="No document data available for sanctions screening.",
            ),
            "errors": state.get("errors", []) + ["sanctions_screener_no_document_data"],
        }

    checks = [
        ("buyer",           watchlist.check_entity(doc.buyer)),
        ("seller",          watchlist.check_entity(doc.seller)),
        ("vessel",          watchlist.check_vessel(doc.vessel_name)),
        ("country_origin",  watchlist.check_country(doc.country_of_origin)),
        ("port_loading",    watchlist.check_port(doc.port_of_loading)),
        ("port_discharge",  watchlist.check_port(doc.port_of_discharge)),
        ("goods",           watchlist.check_goods(doc.goods_description)),
    ]
    raw_hits = [(field, r) for field, r in checks if r["hit"]]
    hits_summary = (
        "\n".join(f"  - {field}: {r['match']} (severity: {r['severity']})" for field, r in raw_hits)
        or "  None"
    )

    model = os.environ["COMPLIANCE_MODEL"]
    llm = ChatAnthropic(model=model)
    structured_llm = llm.with_structured_output(SanctionsResult)

    try:
        result: SanctionsResult = structured_llm.invoke(
            _PROMPT.format(
                buyer=doc.buyer,
                seller=doc.seller,
                vessel_name=doc.vessel_name,
                country_of_origin=doc.country_of_origin,
                port_of_loading=doc.port_of_loading,
                port_of_discharge=doc.port_of_discharge,
                goods_description=doc.goods_description,
                hits_summary=hits_summary,
            )
        )
        logger.info(
            "sanctions_screened",
            hit_count=len(result.hits),
            is_clear=result.is_clear,
            buyer_ref=mask_sensitive_field(doc.buyer),
        )
        return {"sanctions_result": result}
    except Exception as exc:
        logger.error("sanctions_screener_failed", error_type=type(exc).__name__)
        # Preserve raw watchlist hits even if LLM failed
        severities = [r["severity"] for _, r in raw_hits]
        overall_severity = (
            "critical" if "critical" in severities
            else "high" if "high" in severities
            else "medium" if "medium" in severities
            else "none"
        )
        return {
            "sanctions_result": SanctionsResult(
                hits=[f"{field}: {r['match']}" for field, r in raw_hits],
                is_clear=len(raw_hits) == 0,
                severity=overall_severity,
                confidence=0.0,
                summary="Sanctions screening LLM call failed; raw watchlist results preserved.",
            ),
            "errors": state.get("errors", []) + ["sanctions_screener_failed"],
        }
