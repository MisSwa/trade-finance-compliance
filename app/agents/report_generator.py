import os

from langchain_anthropic import ChatAnthropic

from app.models.schemas import ComplianceReport, ComplianceState
from app.utils.logging import get_logger

logger = get_logger(__name__)

_PROMPT = """You are a trade finance compliance officer producing a formal compliance report.

Based on the agent findings below, write a complete compliance report.

Verdict: {verdict}
Risk score: {score} (0 = no risk, 1 = maximum risk)
Overall confidence: {confidence}

Agent findings:
- Sanctions screening: {sanctions_summary}
- Policy check: {policy_summary}
- Consistency check: {consistency_summary}

Risk factors identified:
{risk_factors}

Human review decision (if applicable): {human_decision}

Provide:
- verdict: the final verdict — "clear", "needs_review", or "rejected"
- risk_score: the numeric risk score (0.0–1.0)
- recommendations: list of recommended regulatory or procedural actions
- sar_warranted: true if a Suspicious Activity Report should be considered
- reasoning: full explanation of how the verdict was reached, suitable for audit
- audit_summary: one-paragraph summary for the audit trail
"""


def generate_report(state: ComplianceState) -> dict:
    risk = state.get("risk_result")
    sanctions = state.get("sanctions_result")
    policy = state.get("policy_result")
    consistency = state.get("consistency_result")

    verdict = risk.verdict if risk else "needs_review"
    score = risk.score if risk else 1.0
    confidence = risk.confidence if risk else 0.0
    risk_factors = "\n".join(f"  - {f}" for f in (risk.risk_factors if risk else [])) or "  None"
    human_decision = state.get("human_decision") or "None — automated routing"

    model = os.environ["COMPLIANCE_MODEL"]
    llm = ChatAnthropic(model=model)
    structured_llm = llm.with_structured_output(ComplianceReport)

    try:
        result: ComplianceReport = structured_llm.invoke(
            _PROMPT.format(
                verdict=verdict,
                score=score,
                confidence=confidence,
                sanctions_summary=sanctions.summary if sanctions else "Not available",
                policy_summary=policy.summary if policy else "Not available",
                consistency_summary=consistency.summary if consistency else "Not available",
                risk_factors=risk_factors,
                human_decision=human_decision,
            )
        )
        logger.info("report_generated", verdict=result.verdict, sar_warranted=result.sar_warranted)
        return {"compliance_report": result}
    except Exception as exc:
        logger.error("report_generator_failed", error_type=type(exc).__name__)
        return {
            "compliance_report": ComplianceReport(
                verdict=verdict,
                risk_score=score,
                recommendations=["Manual review required — report generation failed."],
                sar_warranted=False,
                reasoning="Report generation failed due to an internal error.",
                audit_summary=f"Automated report generation failed. Verdict from risk scorer: {verdict}.",
            ),
            "errors": state.get("errors", []) + ["report_generator_failed"],
        }
