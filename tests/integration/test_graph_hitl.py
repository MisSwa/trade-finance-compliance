import pytest
from unittest.mock import MagicMock

from langgraph.types import Command

from app.models.schemas import (
    ComplianceReport, ConsistencyResult, DocumentData,
    PolicyResult, SanctionsResult,
)

_THREAD_PAUSE = "hitl-test-pause-001"
_THREAD_RESUME_APPROVE = "hitl-test-resume-approve-002"
_THREAD_RESUME_REJECT = "hitl-test-resume-reject-003"

_SAMPLE_DOC = DocumentData(
    buyer="Flagged Buyer Corp",
    seller="Reliable Exports GmbH",
    goods_description="Industrial machinery",
    amounts=[50000.0],
    currency="USD",
    country_of_origin="Germany",
    port_of_loading="Hamburg",
    port_of_discharge="Rotterdam",
    vessel_name="MV Sunrise",
    date="2024-03-01",
    doc_type="invoice",
    extraction_confidence=0.9,
)

_FLAGGED_REPORT = ComplianceReport(
    verdict="needs_review",
    risk_score=0.5,
    recommendations=["Escalate to senior compliance officer."],
    sar_warranted=False,
    reasoning="Sanctions hit found in buyer field.",
    audit_summary="Case escalated after human review.",
)


def _patch_all_agents_needs_review(mocker):
    """Mock all LLM agents: sanctions returns is_clear=False → needs_review → interrupt."""
    doc_llm = MagicMock()
    doc_llm.with_structured_output.return_value.invoke.return_value = _SAMPLE_DOC
    mocker.patch("app.agents.document_extractor.ChatAnthropic", return_value=doc_llm)
    mocker.patch("app.agents.document_extractor.extract_text", return_value="Invoice text.")

    sanctions_llm = MagicMock()
    sanctions_llm.with_structured_output.return_value.invoke.return_value = SanctionsResult(
        hits=["buyer: Flagged Buyer Corp (severity: high)"],
        is_clear=False, severity="high", confidence=0.9,
        summary="Sanctioned entity found in buyer field.",
    )
    mocker.patch("app.agents.sanctions_screener.ChatAnthropic", return_value=sanctions_llm)

    policy_llm = MagicMock()
    policy_llm.with_structured_output.return_value.invoke.return_value = PolicyResult(
        violations=[], is_clear=True, confidence=0.92, summary="No violations."
    )
    mocker.patch("app.agents.policy_checker.ChatAnthropic", return_value=policy_llm)

    consistency_llm = MagicMock()
    consistency_llm.with_structured_output.return_value.invoke.return_value = ConsistencyResult(
        discrepancies=[], is_clear=True, confidence=0.91, summary="Consistent."
    )
    mocker.patch("app.agents.consistency_checker.ChatAnthropic", return_value=consistency_llm)

    report_llm = MagicMock()
    report_llm.with_structured_output.return_value.invoke.return_value = _FLAGGED_REPORT
    mocker.patch("app.agents.report_generator.ChatAnthropic", return_value=report_llm)


@pytest.mark.integration
def test_graph_pauses_at_human_review_for_needs_review(mocker):
    _patch_all_agents_needs_review(mocker)

    from app.graph.workflow import graph, run_graph

    run_graph(["fake_invoice.pdf"], None, _THREAD_PAUSE)

    config = {"configurable": {"thread_id": _THREAD_PAUSE}}
    state = graph.get_state(config)
    assert "human_review" in state.next


@pytest.mark.integration
def test_command_resume_approve_produces_final_report(mocker):
    _patch_all_agents_needs_review(mocker)

    from app.graph.workflow import graph, run_graph

    run_graph(["fake_invoice.pdf"], None, _THREAD_RESUME_APPROVE)
    config = {"configurable": {"thread_id": _THREAD_RESUME_APPROVE}}
    assert "human_review" in graph.get_state(config).next

    final_state = run_graph(
        document_paths=[],
        policy_path=None,
        thread_id=_THREAD_RESUME_APPROVE,
        resume_command=Command(resume="approve"),
    )

    assert final_state["human_decision"] == "approve"
    assert final_state["compliance_report"] is not None


@pytest.mark.integration
def test_command_resume_reject_sets_human_decision(mocker):
    _patch_all_agents_needs_review(mocker)

    from app.graph.workflow import graph, run_graph

    run_graph(["fake_invoice.pdf"], None, _THREAD_RESUME_REJECT)
    config = {"configurable": {"thread_id": _THREAD_RESUME_REJECT}}
    assert "human_review" in graph.get_state(config).next

    final_state = run_graph(
        document_paths=[],
        policy_path=None,
        thread_id=_THREAD_RESUME_REJECT,
        resume_command=Command(resume="reject"),
    )

    assert final_state["human_decision"] == "reject"
    assert final_state["compliance_report"] is not None
