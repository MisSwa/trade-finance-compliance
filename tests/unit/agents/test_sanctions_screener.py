import pytest
from unittest.mock import MagicMock, patch

from app.models.schemas import DocumentData, SanctionsResult
from app.agents.sanctions_screener import screen_sanctions

_CLEAN_DOC = DocumentData(
    buyer="Good Faith Importers Ltd",
    seller="Reliable Exports GmbH",
    goods_description="Cotton textiles",
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

_FLAGGED_DOC = DocumentData(
    buyer="Zarkon Trading Corporation",
    seller="Reliable Exports GmbH",
    goods_description="Cotton textiles",
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
    mocker.patch("app.agents.sanctions_screener.ChatAnthropic", return_value=mock_llm)
    return mock_llm


@pytest.mark.unit
def test_flagged_document_returns_not_clear(mocker):
    _mock_llm(mocker, return_value=SanctionsResult(
        hits=["buyer: Zarkon Trading Corporation (severity: critical)"],
        is_clear=False,
        severity="critical",
        confidence=0.95,
        summary="Sanctioned entity found in buyer field.",
    ))
    state = {**_BASE_STATE, "document_data": _FLAGGED_DOC}

    result = screen_sanctions(state)

    assert result["sanctions_result"].is_clear is False
    assert len(result["sanctions_result"].hits) > 0


@pytest.mark.unit
def test_clean_document_returns_clear(mocker):
    _mock_llm(mocker, return_value=SanctionsResult(
        hits=[], is_clear=True, severity="none", confidence=0.95, summary="No hits found."
    ))
    state = {**_BASE_STATE, "document_data": _CLEAN_DOC}

    result = screen_sanctions(state)

    assert result["sanctions_result"].is_clear is True
    assert result["sanctions_result"].hits == []


@pytest.mark.unit
def test_llm_exception_returns_zero_confidence_and_appends_error(mocker):
    _mock_llm(mocker, side_effect=Exception("LLM unavailable"))
    state = {**_BASE_STATE, "document_data": _CLEAN_DOC}

    result = screen_sanctions(state)

    assert result["sanctions_result"].confidence == 0.0
    assert "sanctions_screener_failed" in result["errors"]


@pytest.mark.unit
def test_node_only_returns_its_own_keys(mocker):
    _mock_llm(mocker, return_value=SanctionsResult(
        hits=[], is_clear=True, severity="none", confidence=0.9, summary="Clear."
    ))
    state = {**_BASE_STATE, "document_data": _CLEAN_DOC}

    result = screen_sanctions(state)

    assert "policy_result" not in result
    assert "consistency_result" not in result
    assert "risk_result" not in result
    assert "document_data" not in result
