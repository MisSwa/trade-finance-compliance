import pytest
from unittest.mock import MagicMock

from app.models.schemas import DocumentData, ConsistencyResult
from app.agents.consistency_checker import check_consistency

_CONSISTENT_DOC = DocumentData(
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

_INCONSISTENT_DOC = DocumentData(
    buyer="Good Faith Importers Ltd",
    seller="Reliable Exports GmbH",
    goods_description="General merchandise",
    amounts=[9999999.0],
    currency="USD",
    country_of_origin="Ruritania",
    port_of_loading="Hamburg",
    port_of_discharge="Rotterdam",
    vessel_name="MV Sunrise",
    date="2024-03-01",
    doc_type="invoice",
    extraction_confidence=0.6,
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
    mocker.patch("app.agents.consistency_checker.ChatAnthropic", return_value=mock_llm)
    return mock_llm


@pytest.mark.unit
def test_inconsistent_document_returns_discrepancies(mocker):
    _mock_llm(mocker, return_value=ConsistencyResult(
        discrepancies=["Amount USD 9,999,999 implausible for general merchandise"],
        is_clear=False,
        confidence=0.88,
        summary="Implausible amount relative to goods description.",
    ))
    state = {**_BASE_STATE, "document_data": _INCONSISTENT_DOC}

    result = check_consistency(state)

    assert result["consistency_result"].is_clear is False
    assert len(result["consistency_result"].discrepancies) > 0


@pytest.mark.unit
def test_consistent_document_returns_clear(mocker):
    _mock_llm(mocker, return_value=ConsistencyResult(
        discrepancies=[], is_clear=True, confidence=0.94, summary="No inconsistencies found."
    ))
    state = {**_BASE_STATE, "document_data": _CONSISTENT_DOC}

    result = check_consistency(state)

    assert result["consistency_result"].is_clear is True
    assert result["consistency_result"].discrepancies == []


@pytest.mark.unit
def test_llm_exception_returns_zero_confidence_and_appends_error(mocker):
    _mock_llm(mocker, side_effect=Exception("parse error"))
    state = {**_BASE_STATE, "document_data": _CONSISTENT_DOC}

    result = check_consistency(state)

    assert result["consistency_result"].confidence == 0.0
    assert "consistency_checker_failed" in result["errors"]


@pytest.mark.unit
def test_node_only_returns_its_own_keys(mocker):
    _mock_llm(mocker, return_value=ConsistencyResult(
        discrepancies=[], is_clear=True, confidence=0.9, summary="Clear."
    ))
    state = {**_BASE_STATE, "document_data": _CONSISTENT_DOC}

    result = check_consistency(state)

    assert "sanctions_result" not in result
    assert "policy_result" not in result
    assert "risk_result" not in result
    assert "document_data" not in result
