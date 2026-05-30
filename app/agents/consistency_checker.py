import os

from langchain_anthropic import ChatAnthropic

from app.models.schemas import ComplianceState, ConsistencyResult
from app.utils.logging import get_logger

logger = get_logger(__name__)

_PROMPT = """You are a trade finance document consistency analyst.

Review the extracted document data below and identify any internal inconsistencies that may indicate fraud, error, or trade-based money laundering.

Common inconsistency patterns to check:
- Declared amounts that appear implausible for the goods described
- Vague or generic goods descriptions that obscure the nature of the shipment
- Mismatched country of origin vs port of loading geography
- Doc type inconsistent with the content (e.g. invoice fields in a B/L)
- Missing critical fields (empty buyer, seller, or goods description)

Document data:
- Doc type: {doc_type}
- Buyer: {buyer}
- Seller: {seller}
- Goods: {goods_description}
- Amounts: {amounts} {currency}
- Country of origin: {country_of_origin}
- Port of loading: {port_of_loading}
- Port of discharge: {port_of_discharge}
- Vessel: {vessel_name}
- Date: {date}
- Extraction confidence: {extraction_confidence}

Provide:
- discrepancies: list of inconsistencies found (empty list if none)
- is_clear: true only if no discrepancies were found
- confidence: your confidence in this assessment (0.0–1.0)
- summary: a concise consistency finding for a compliance officer
"""


def check_consistency(state: ComplianceState) -> dict:
    doc = state.get("document_data")
    if doc is None:
        return {
            "consistency_result": ConsistencyResult(
                discrepancies=[],
                is_clear=False,
                confidence=0.0,
                summary="No document data available for consistency check.",
            ),
            "errors": state.get("errors", []) + ["consistency_checker_no_document_data"],
        }

    model = os.environ["COMPLIANCE_MODEL"]
    llm = ChatAnthropic(model=model)
    structured_llm = llm.with_structured_output(ConsistencyResult)

    try:
        result: ConsistencyResult = structured_llm.invoke(
            _PROMPT.format(
                doc_type=doc.doc_type,
                buyer=doc.buyer,
                seller=doc.seller,
                goods_description=doc.goods_description,
                amounts=doc.amounts,
                currency=doc.currency,
                country_of_origin=doc.country_of_origin,
                port_of_loading=doc.port_of_loading,
                port_of_discharge=doc.port_of_discharge,
                vessel_name=doc.vessel_name,
                date=doc.date,
                extraction_confidence=doc.extraction_confidence,
            )
        )
        logger.info(
            "consistency_checked",
            discrepancy_count=len(result.discrepancies),
            is_clear=result.is_clear,
        )
        return {"consistency_result": result}
    except Exception as exc:
        logger.error("consistency_checker_failed", error_type=type(exc).__name__)
        return {
            "consistency_result": ConsistencyResult(
                discrepancies=[],
                is_clear=False,
                confidence=0.0,
                summary="Consistency check LLM call failed.",
            ),
            "errors": state.get("errors", []) + ["consistency_checker_failed"],
        }
