import pytest
from unittest.mock import MagicMock

from app.agents.document_extractor import extract_documents
from app.models.schemas import (
    ComplianceReport,
    ConsistencyResult,
    DocumentData,
    PolicyResult,
    SanctionsResult,
)

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
    "thread_id": "hardening-test-thread",
}

_SAMPLE_DOC = DocumentData(
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
    extraction_confidence=0.90,
)

_SAMPLE_REPORT = ComplianceReport(
    verdict="needs_review",
    risk_score=0.5,
    recommendations=["Review required."],
    sar_warranted=False,
    reasoning="Low confidence due to agent failure.",
    audit_summary="Escalated after agent exception.",
)


# ---------------------------------------------------------------------------
# Test 1: Unreadable PDF guard
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_unreadable_pdf_sets_zero_confidence_and_appends_error(mocker):
    """When extracted text is < 100 chars the extractor skips the LLM call,
    returns extraction_confidence=0.0, and appends an error key."""
    mocker.patch("app.agents.document_extractor.extract_text", return_value="")
    mock_anthropic = mocker.patch("app.agents.document_extractor.ChatAnthropic")

    result = extract_documents(_BASE_STATE)

    assert result["document_data"].extraction_confidence == 0.0
    assert "document_extractor_unreadable_pdf" in result.get("errors", [])
    mock_anthropic.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2: Agent exception routes to human_review
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_agent_exception_does_not_crash_graph_and_routes_to_human_review(mocker):
    """If an agent raises RuntimeError the graph catches it, captures the error
    in state, and pauses at human_review (due to confidence=0.0 from the failed agent).
    The graph does not crash."""
    # Extractor succeeds
    doc_llm = MagicMock()
    doc_llm.with_structured_output.return_value.invoke.return_value = _SAMPLE_DOC
    mocker.patch("app.agents.document_extractor.ChatAnthropic", return_value=doc_llm)
    mocker.patch(
        "app.agents.document_extractor.extract_text",
        return_value="Invoice text content — sufficient length for the guard check.",
    )

    # Sanctions screener raises RuntimeError (e.g. network error)
    sanctions_llm = MagicMock()
    sanctions_llm.with_structured_output.return_value.invoke.side_effect = RuntimeError(
        "Simulated network error"
    )
    mocker.patch("app.agents.sanctions_screener.ChatAnthropic", return_value=sanctions_llm)

    # Other agents return clear results
    policy_llm = MagicMock()
    policy_llm.with_structured_output.return_value.invoke.return_value = PolicyResult(
        violations=[], is_clear=True, confidence=0.95, summary="No violations."
    )
    mocker.patch("app.agents.policy_checker.ChatAnthropic", return_value=policy_llm)

    consistency_llm = MagicMock()
    consistency_llm.with_structured_output.return_value.invoke.return_value = ConsistencyResult(
        discrepancies=[], is_clear=True, confidence=0.95, summary="Consistent."
    )
    mocker.patch("app.agents.consistency_checker.ChatAnthropic", return_value=consistency_llm)

    report_llm = MagicMock()
    report_llm.with_structured_output.return_value.invoke.return_value = _SAMPLE_REPORT
    mocker.patch("app.agents.report_generator.ChatAnthropic", return_value=report_llm)

    from app.graph.workflow import graph, run_graph

    thread_id = "hardening-exception-test-001"
    run_graph(["fake_invoice.pdf"], None, thread_id)

    config = {"configurable": {"thread_id": thread_id}}
    gs = graph.get_state(config)

    assert "sanctions_screener_failed" in gs.values["errors"]
    assert "human_review" in gs.next
