import pytest
from unittest.mock import MagicMock

from app.models.schemas import (
    ComplianceReport, ConsistencyResult, DocumentData,
    PolicyResult, SanctionsResult,
)

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
    extraction_confidence=0.95,
)

_MOCK_REPORT = ComplianceReport(
    verdict="clear",
    risk_score=0.0,
    recommendations=["No further action required."],
    sar_warranted=False,
    reasoning="All agents returned clear with high confidence.",
    audit_summary="Transaction cleared by automated compliance review.",
)


def _patch_all_agents_clear(mocker):
    """Mock all LLM agents with clear+high-confidence results so the graph
    routes directly to report_generator without pausing at human_review."""
    doc_llm = MagicMock()
    doc_llm.with_structured_output.return_value.invoke.return_value = _SAMPLE_DOC
    mocker.patch("app.agents.document_extractor.ChatAnthropic", return_value=doc_llm)
    mocker.patch("app.agents.document_extractor.extract_text", return_value="Invoice text content — sufficient length for extraction testing. This string is intentionally over one hundred characters long.")

    sanctions_llm = MagicMock()
    sanctions_llm.with_structured_output.return_value.invoke.return_value = SanctionsResult(
        hits=[], is_clear=True, severity="none", confidence=0.95,
        summary="No sanctions hits found.",
    )
    mocker.patch("app.agents.sanctions_screener.ChatAnthropic", return_value=sanctions_llm)

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
    report_llm.with_structured_output.return_value.invoke.return_value = _MOCK_REPORT
    mocker.patch("app.agents.report_generator.ChatAnthropic", return_value=report_llm)


@pytest.mark.integration
def test_graph_completes_with_populated_document_data(mocker):
    _patch_all_agents_clear(mocker)

    from app.graph.workflow import run_graph

    final_state = run_graph(
        document_paths=["fake_invoice.pdf"],
        policy_path=None,
        thread_id="routing-test-001",
    )

    assert final_state["document_data"] is not None
    assert isinstance(final_state["document_data"], DocumentData)
    assert final_state["document_data"].extraction_confidence > 0
    assert final_state["errors"] == []
    assert final_state["compliance_report"] is not None


@pytest.mark.integration
def test_graph_handles_extractor_failure_without_crashing(mocker):
    """When extractor fails the graph continues: errors are captured and the
    parallel agents (mocked clear) still route to report_generator."""
    doc_llm = MagicMock()
    doc_llm.with_structured_output.return_value.invoke.side_effect = Exception("Simulated LLM failure")
    mocker.patch("app.agents.document_extractor.ChatAnthropic", return_value=doc_llm)
    mocker.patch("app.agents.document_extractor.extract_text", return_value="Invoice text content — sufficient length for extraction testing. This string is intentionally over one hundred characters long.")

    sanctions_llm = MagicMock()
    sanctions_llm.with_structured_output.return_value.invoke.return_value = SanctionsResult(
        hits=[], is_clear=True, severity="none", confidence=0.95,
        summary="No sanctions hits found.",
    )
    mocker.patch("app.agents.sanctions_screener.ChatAnthropic", return_value=sanctions_llm)

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
    report_llm.with_structured_output.return_value.invoke.return_value = _MOCK_REPORT
    mocker.patch("app.agents.report_generator.ChatAnthropic", return_value=report_llm)

    from app.graph.workflow import run_graph

    final_state = run_graph(
        document_paths=["fake_invoice.pdf"],
        policy_path=None,
        thread_id="routing-test-002",
    )

    assert "document_extractor_failed" in final_state["errors"]
    assert final_state["document_data"].extraction_confidence == 0.0
    assert final_state["compliance_report"] is not None


@pytest.mark.integration
def test_graph_full_pipeline_populates_all_result_fields(mocker):
    """All intermediate result fields are set when the full pipeline runs."""
    _patch_all_agents_clear(mocker)

    from app.graph.workflow import run_graph

    final_state = run_graph(
        document_paths=["fake_invoice.pdf"],
        policy_path=None,
        thread_id="routing-test-003",
    )

    assert final_state["sanctions_result"] is not None
    assert final_state["policy_result"] is not None
    assert final_state["consistency_result"] is not None
    assert final_state["risk_result"] is not None
    assert final_state["compliance_report"] is not None
    # Clear path routes directly to report_generator — no human decision
    assert final_state["human_decision"] is None
