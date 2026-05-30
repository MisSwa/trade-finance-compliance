from app.models.schemas import ComplianceState, RiskResult
from app.utils.logging import get_logger

logger = get_logger(__name__)


def score_risk(state: ComplianceState) -> dict:
    sanctions = state.get("sanctions_result")
    policy = state.get("policy_result")
    consistency = state.get("consistency_result")

    results = [r for r in (sanctions, policy, consistency) if r is not None]

    try:
        # Verdict: highest severity wins
        if sanctions and not sanctions.is_clear and sanctions.severity == "critical":
            verdict = "rejected"
        elif any(not r.is_clear for r in results):
            verdict = "needs_review"
        else:
            verdict = "clear"

        # Risk score: confidence-weighted proportion of positive findings
        if results:
            score = sum(r.confidence for r in results if not r.is_clear) / len(results)
            overall_confidence = min(r.confidence for r in results)
        else:
            score = 1.0
            overall_confidence = 0.0

        risk_factors: list[str] = []
        if sanctions and not sanctions.is_clear:
            risk_factors.append(f"Sanctions: {sanctions.summary}")
        if policy and not policy.is_clear:
            risk_factors.append(f"Policy: {policy.summary}")
        if consistency and not consistency.is_clear:
            risk_factors.append(f"Consistency: {consistency.summary}")

        result = RiskResult(
            score=round(min(max(score, 0.0), 1.0), 4),
            verdict=verdict,
            confidence=round(overall_confidence, 4),
            risk_factors=risk_factors,
        )
        logger.info("risk_scored", verdict=result.verdict, score=result.score, confidence=result.confidence)
        return {"risk_result": result}

    except Exception as exc:
        logger.error("risk_scorer_failed", error_type=type(exc).__name__)
        return {
            "risk_result": RiskResult(
                score=1.0,
                verdict="needs_review",
                confidence=0.0,
                risk_factors=["risk_scorer_failed"],
            ),
            "errors": state.get("errors", []) + ["risk_scorer_failed"],
        }
