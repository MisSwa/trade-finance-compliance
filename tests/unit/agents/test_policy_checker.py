import pytest
from unittest.mock import MagicMock

from app.models.schemas import DocumentData, PolicyResult
from app.agents.policy_checker import check_policy

_CLEAN_DOC = DocumentData(
    buyer="Good Faith Importers Ltd",
    seller="Reliable Exports GmbH",
    goods_description="Industrial machinery parts, HS 8484.10.00",
    amounts=[50000.0],
    currency="USD",
    country_of_origin="Germany",
    port_of_loading="Hamburg",
    port_of_discharge="Rotterdam",
    vessel_name="MV Sunrise",
    date="2024-03-01",
    doc_type="invoice",
    extraction_confidence=0.95,
)

_POLICY_VIOLATION_DOC = DocumentData(
    buyer="Obscure Holdings Ltd",
    seller="Zarkon Trading Corporation",
    goods_description="General merchandise",
    amounts=[500000.0],
    currency="USD",
    country_of_origin="Ruritania",
    port_of_loading="Port Obscura",
    port_of_discharge="Darkwater Terminal",
    vessel_name="MV Phantom Star",
    date="2024-03-10",
    doc_type="invoice",
    extraction_confidence=0.85,
)

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


def _mock_llm(mocker, return_value=None, side_effect=None):
    mock_structured = MagicMock()
    if side_effect:
        mock_structured.invoke.side_effect = side_effect
    else:
        mock_structured.invoke.return_value = return_value
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mocker.patch("app.agents.policy_checker.ChatAnthropic", return_value=mock_llm)
    return mock_llm


@pytest.mark.unit
def test_policy_violation_returns_not_clear(mocker):
    _mock_llm(mocker, return_value=PolicyResult(
        violations=["Advance payment to high-risk jurisdiction exceeds USD 100,000"],
        is_clear=False,
        confidence=0.9,
        summary="Prohibited payment terms for high-risk jurisdiction.",
    ))
    state = {**_BASE_STATE, "document_data": _POLICY_VIOLATION_DOC}

    result = check_policy(state)

    assert result["policy_result"].is_clear is False
    assert len(result["policy_result"].violations) > 0


@pytest.mark.unit
def test_clean_document_no_policy_returns_clear(mocker):
    _mock_llm(mocker, return_value=PolicyResult(
        violations=[], is_clear=True, confidence=0.92, summary="No policy violations found."
    ))
    state = {**_BASE_STATE, "document_data": _CLEAN_DOC}

    result = check_policy(state)

    assert result["policy_result"].is_clear is True
    assert result["policy_result"].violations == []


@pytest.mark.unit
def test_llm_exception_returns_zero_confidence_and_appends_error(mocker):
    _mock_llm(mocker, side_effect=RuntimeError("timeout"))
    state = {**_BASE_STATE, "document_data": _CLEAN_DOC}

    result = check_policy(state)

    assert result["policy_result"].confidence == 0.0
    assert "policy_checker_failed" in result["errors"]


@pytest.mark.unit
def test_node_only_returns_its_own_keys(mocker):
    _mock_llm(mocker, return_value=PolicyResult(
        violations=[], is_clear=True, confidence=0.9, summary="Clear."
    ))
    state = {**_BASE_STATE, "document_data": _CLEAN_DOC}

    result = check_policy(state)

    assert "sanctions_result" not in result
    assert "consistency_result" not in result
    assert "risk_result" not in result
    assert "document_data" not in result
