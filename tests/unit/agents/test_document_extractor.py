import pytest
from unittest.mock import MagicMock

from app.models.schemas import DocumentData
from app.agents.document_extractor import extract_documents

_BASE_STATE = {
    "document_paths": ["tests/fixtures/sample_invoice.txt"],
    "policy_path": None,
    "document_data": None,
    "sanctions_result": None,
    "policy_result": None,
    "consistency_result": None,
    "risk_result": None,
    "compliance_report": None,
    "human_decision": None,
    "errors": [],
    "thread_id": "test-thread-001",
}

_SAMPLE_DOC_DATA = DocumentData(
    buyer="Good Faith Importers Ltd",
    seller="Reliable Exports GmbH",
    goods_description="Industrial machinery parts",
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


def _mock_llm(mocker, return_value=None, side_effect=None):
    mock_structured = MagicMock()
    if side_effect:
        mock_structured.invoke.side_effect = side_effect
    else:
        mock_structured.invoke.return_value = return_value
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mocker.patch("app.agents.document_extractor.ChatAnthropic", return_value=mock_llm)
    mocker.patch(
        "app.agents.document_extractor.extract_text",
        return_value=(
            "Invoice text content — sufficient length for extraction testing. "
            "This string is intentionally over one hundred characters long."
        ),
    )
    return mock_llm


@pytest.mark.unit
def test_successful_extraction_returns_document_data(mocker):
    _mock_llm(mocker, return_value=_SAMPLE_DOC_DATA)

    result = extract_documents(_BASE_STATE)

    assert isinstance(result["document_data"], DocumentData)
    assert result["document_data"].extraction_confidence == 0.95
    assert result["document_data"].buyer == "Good Faith Importers Ltd"


@pytest.mark.unit
def test_llm_exception_sets_zero_confidence_and_appends_error(mocker):
    _mock_llm(mocker, side_effect=Exception("LLM unavailable"))

    result = extract_documents(_BASE_STATE)

    assert result["document_data"].extraction_confidence == 0.0
    assert "document_extractor_failed" in result["errors"]


@pytest.mark.unit
def test_node_only_returns_keys_it_updates(mocker):
    _mock_llm(mocker, return_value=_SAMPLE_DOC_DATA)

    result = extract_documents(_BASE_STATE)

    assert "sanctions_result" not in result
    assert "risk_result" not in result
    assert "compliance_report" not in result
    assert "human_decision" not in result
    assert "policy_result" not in result


@pytest.mark.unit
def test_error_is_appended_to_existing_errors(mocker):
    _mock_llm(mocker, side_effect=ValueError("Structured output parse failure"))
    state = {**_BASE_STATE, "errors": ["prior_error"]}

    result = extract_documents(state)

    assert "prior_error" in result["errors"]
    assert "document_extractor_failed" in result["errors"]


@pytest.mark.unit
def test_failed_extraction_returns_unknown_doc_type(mocker):
    _mock_llm(mocker, side_effect=RuntimeError("timeout"))

    result = extract_documents(_BASE_STATE)

    assert result["document_data"].doc_type == "unknown"
