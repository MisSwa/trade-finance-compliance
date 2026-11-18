import os

from langchain_anthropic import ChatAnthropic

from app.models.schemas import ComplianceState, PolicyResult
from app.tools.pdf_reader import extract_text
from app.utils.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_POLICY = """Standard trade finance policy rules:
- Advance payment terms for transactions exceeding USD 100,000 to high-risk jurisdictions are prohibited.
- Goods must have a valid HS code specified.
- Buyer and seller names must be verifiable and not use generic terms.
- Transactions involving free trade zones in high-risk jurisdictions require enhanced due diligence.
"""

_PROMPT = """You are a trade finance policy compliance analyst.

Review the trade document data below against the bank policy and identify any violations.

Document data:
- Buyer: {buyer}
- Seller: {seller}
- Goods: {goods_description}
- Amounts: {amounts}
- Currency: {currency}
- Country of origin: {country_of_origin}
- Port of loading: {port_of_loading}
- Port of discharge: {port_of_discharge}
- Payment terms context: {doc_type} document
- Date: {date}

Bank policy:
{policy_text}

Provide:
- violations: list of policy rule violations found (empty list if none)
- is_clear: true only if no violations were found
- confidence: your confidence in this assessment (0.0–1.0)
- summary: a concise compliance finding for a policy officer
"""


def check_policy(state: ComplianceState) -> dict:
    doc = state.get("document_data")
    if doc is None:
        return {
            "policy_result": PolicyResult(
                violations=[],
                is_clear=False,
                confidence=0.0,
                summary="No document data available for policy check.",
            ),
            "errors": state.get("errors", []) + ["policy_checker_no_document_data"],
        }

    policy_text = _DEFAULT_POLICY
    if state.get("policy_path"):
        extracted = extract_text(state["policy_path"])
        if extracted:
            policy_text = extracted

    model = os.environ["COMPLIANCE_MODEL"]
    llm = ChatAnthropic(model=model)
    structured_llm = llm.with_structured_output(PolicyResult)

    try:
        result: PolicyResult = structured_llm.invoke(
            _PROMPT.format(
                buyer=doc.buyer,
                seller=doc.seller,
                goods_description=doc.goods_description,
                amounts=doc.amounts,
                currency=doc.currency,
                country_of_origin=doc.country_of_origin,
                port_of_loading=doc.port_of_loading,
                port_of_discharge=doc.port_of_discharge,
                doc_type=doc.doc_type,
                date=doc.date,
                policy_text=policy_text,
            )
        )
        logger.info(
            "policy_checked",
            violation_count=len(result.violations),
            is_clear=result.is_clear,
        )
        return {"policy_result": result}
    except Exception as exc:
        logger.error("policy_checker_failed", error_type=type(exc).__name__)
        return {
            "policy_result": PolicyResult(
                violations=[],
                is_clear=False,
                confidence=0.0,
                summary="Policy check LLM call failed.",
            ),
            "errors": state.get("errors", []) + ["policy_checker_failed"],
        }
