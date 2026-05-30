import pytest
from unittest.mock import MagicMock

from app.models.schemas import DocumentData

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


def _patch_extractor(mocker, return_value=None, side_effect=None):
    mock_structured = MagicMock()
    if side_effect:
        mock_structured.invoke.side_effect = side_effect
    else:
        mock_structured.invoke.return_value = return_value
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mocker.patch("app.agents.document_extractor.ChatAnthropic", return_value=mock_llm)
    mocker.patch("app.agents.document_extractor.extract_text", return_value="Invoice content.")


@pytest.mark.integration
def test_graph_completes_with_populated_document_data(mocker):
    _patch_extractor(mocker, return_value=_SAMPLE_DOC_DATA)

    from app.graph.workflow import run_graph

    final_state = run_graph(
        document_paths=["fake_invoice.pdf"],
        policy_path=None,
        thread_id="integration-test-001",
    )

    assert final_state["document_data"] is not None
    assert isinstance(final_state["document_data"], DocumentData)
    assert final_state["document_data"].extraction_confidence > 0
    assert final_state["errors"] == []


@pytest.mark.integration
def test_graph_handles_extractor_failure_without_crashing(mocker):
    _patch_extractor(mocker, side_effect=Exception("Simulated LLM failure"))

    from app.graph.workflow import run_graph

    final_state = run_graph(
        document_paths=["fake_invoice.pdf"],
        policy_path=None,
        thread_id="integration-test-002",
    )

    assert "document_extractor_failed" in final_state["errors"]
    assert final_state["document_data"].extraction_confidence == 0.0


@pytest.mark.integration
def test_graph_initial_state_fields_preserved(mocker):
    _patch_extractor(mocker, return_value=_SAMPLE_DOC_DATA)

    from app.graph.workflow import run_graph

    final_state = run_graph(
        document_paths=["fake_invoice.pdf"],
        policy_path=None,
        thread_id="integration-test-003",
    )

    # Fields not touched by the extractor node stay None
    assert final_state["sanctions_result"] is None
    assert final_state["risk_result"] is None
    assert final_state["compliance_report"] is None
    assert final_state["human_decision"] is None
