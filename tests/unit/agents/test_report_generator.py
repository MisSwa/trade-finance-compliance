import pytest
from unittest.mock import MagicMock

from app.models.schemas import (
    ComplianceReport, DocumentData, RiskResult,
    SanctionsResult, PolicyResult, ConsistencyResult,
)
from app.agents.report_generator import generate_report

_BASE_STATE = {
    "document_paths": [],
    "policy_path": None,
    "document_data": None,
    "sanctions_result": SanctionsResult(hits=[], is_clear=True, severity="none", confidence=0.95, summary="No hits."),
    "policy_result": PolicyResult(violations=[], is_clear=True, confidence=0.93, summary="No violations."),
    "consistency_result": ConsistencyResult(discrepancies=[], is_clear=True, confidence=0.91, summary="Consistent."),
    "risk_result": RiskResult(score=0.0, verdict="clear", confidence=0.91, risk_factors=[]),
    "compliance_report": None,
    "human_decision": None,
    "errors": [],
    "thread_id": "test-thread",
}

_CLEAR_REPORT = ComplianceReport(
    verdict="clear",
    risk_score=0.0,
    recommendations=["No action required."],
    sar_warranted=False,
    reasoning="All agents returned clear with high confidence.",
    audit_summary="Transaction cleared by automated review.",
)


def _mock_llm(mocker, return_value=None, side_effect=None):
    mock_structured = MagicMock()
    if side_effect:
        mock_structured.invoke.side_effect = side_effect
    else:
        mock_structured.invoke.return_value = return_value
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mocker.patch("app.agents.report_generator.ChatAnthropic", return_value=mock_llm)
    return mock_llm


@pytest.mark.unit
def test_full_clean_state_returns_clear_report(mocker):
    _mock_llm(mocker, return_value=_CLEAR_REPORT)

    result = generate_report(_BASE_STATE)

    assert isinstance(result["compliance_report"], ComplianceReport)
    assert result["compliance_report"].verdict == "clear"
    assert result["compliance_report"].sar_warranted is False


@pytest.mark.unit
def test_human_decision_present_in_prompt(mocker):
    captured_prompts = []
    mock_structured = MagicMock()
    mock_structured.invoke.side_effect = lambda prompt: (captured_prompts.append(prompt) or _CLEAR_REPORT)
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mocker.patch("app.agents.report_generator.ChatAnthropic", return_value=mock_llm)

    state = {**_BASE_STATE, "human_decision": "approve"}
    generate_report(state)

    assert any("approve" in p for p in captured_prompts)


@pytest.mark.unit
def test_llm_exception_returns_minimal_report_and_appends_error(mocker):
    _mock_llm(mocker, side_effect=Exception("LLM failure"))

    result = generate_report(_BASE_STATE)

    assert result["compliance_report"].verdict == "clear"  # falls back to risk_result.verdict
    assert "report_generator_failed" in result["errors"]


@pytest.mark.unit
def test_node_only_returns_its_own_keys(mocker):
    _mock_llm(mocker, return_value=_CLEAR_REPORT)

    result = generate_report(_BASE_STATE)

    assert "risk_result" not in result
    assert "sanctions_result" not in result
    assert "document_data" not in result
    assert "human_decision" not in result
