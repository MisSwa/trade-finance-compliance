import pytest
from app.models.schemas import SanctionsResult, PolicyResult, ConsistencyResult
from app.agents.risk_scorer import score_risk

_BASE_STATE = {
    "document_paths": [],
    "policy_path": None,
    "document_data": None,
    "sanctions_result": None,
    "policy_result": None,
    "consistency_result": None,
    "risk_result": None,
    "compliance_report": None,
    "human_decision": None,
    "errors": [],
    "thread_id": "test-thread",
}

_CLEAR_SANCTIONS = SanctionsResult(hits=[], is_clear=True, severity="none", confidence=0.95, summary="Clear.")
_CLEAR_POLICY = PolicyResult(violations=[], is_clear=True, confidence=0.93, summary="Clear.")
_CLEAR_CONSISTENCY = ConsistencyResult(discrepancies=[], is_clear=True, confidence=0.91, summary="Clear.")

_FLAGGED_SANCTIONS = SanctionsResult(hits=["buyer: Zarkon"], is_clear=False, severity="high", confidence=0.9, summary="Hit found.")
_CRITICAL_SANCTIONS = SanctionsResult(hits=["buyer: Zarkon"], is_clear=False, severity="critical", confidence=0.95, summary="Critical hit.")
_FLAGGED_POLICY = PolicyResult(violations=["Advance payment violation"], is_clear=False, confidence=0.88, summary="Violation found.")


@pytest.mark.unit
def test_all_clear_high_confidence_returns_clear_verdict():
    state = {**_BASE_STATE, "sanctions_result": _CLEAR_SANCTIONS, "policy_result": _CLEAR_POLICY, "consistency_result": _CLEAR_CONSISTENCY}

    result = score_risk(state)

    assert result["risk_result"].verdict == "clear"
    assert result["risk_result"].score == 0.0


@pytest.mark.unit
def test_flagged_sanctions_returns_needs_review():
    state = {**_BASE_STATE, "sanctions_result": _FLAGGED_SANCTIONS, "policy_result": _CLEAR_POLICY, "consistency_result": _CLEAR_CONSISTENCY}

    result = score_risk(state)

    assert result["risk_result"].verdict == "needs_review"


@pytest.mark.unit
def test_critical_sanctions_returns_rejected():
    state = {**_BASE_STATE, "sanctions_result": _CRITICAL_SANCTIONS, "policy_result": _CLEAR_POLICY, "consistency_result": _CLEAR_CONSISTENCY}

    result = score_risk(state)

    assert result["risk_result"].verdict == "rejected"


@pytest.mark.unit
def test_all_clear_low_confidence_returns_clear_with_low_confidence():
    low_conf_sanctions = SanctionsResult(hits=[], is_clear=True, severity="none", confidence=0.5, summary="Clear but uncertain.")
    state = {**_BASE_STATE, "sanctions_result": low_conf_sanctions, "policy_result": _CLEAR_POLICY, "consistency_result": _CLEAR_CONSISTENCY}

    result = score_risk(state)

    assert result["risk_result"].verdict == "clear"
    assert result["risk_result"].confidence < 0.7  # routing to human_review is workflow's job


@pytest.mark.unit
def test_policy_violation_returns_needs_review():
    state = {**_BASE_STATE, "sanctions_result": _CLEAR_SANCTIONS, "policy_result": _FLAGGED_POLICY, "consistency_result": _CLEAR_CONSISTENCY}

    result = score_risk(state)

    assert result["risk_result"].verdict == "needs_review"


@pytest.mark.unit
def test_overall_confidence_is_minimum_across_agents():
    state = {**_BASE_STATE, "sanctions_result": _CLEAR_SANCTIONS, "policy_result": _CLEAR_POLICY, "consistency_result": _CLEAR_CONSISTENCY}

    result = score_risk(state)

    assert result["risk_result"].confidence == min(0.95, 0.93, 0.91)


@pytest.mark.unit
def test_node_only_returns_its_own_keys():
    state = {**_BASE_STATE, "sanctions_result": _CLEAR_SANCTIONS, "policy_result": _CLEAR_POLICY, "consistency_result": _CLEAR_CONSISTENCY}

    result = score_risk(state)

    assert "sanctions_result" not in result
    assert "policy_result" not in result
    assert "consistency_result" not in result
    assert "document_data" not in result
