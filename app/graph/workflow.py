import os

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.agents.consistency_checker import check_consistency
from app.agents.document_extractor import extract_documents
from app.agents.policy_checker import check_policy
from app.agents.report_generator import generate_report
from app.agents.risk_scorer import score_risk
from app.agents.sanctions_screener import screen_sanctions
from app.models.schemas import ComplianceState


def route_after_risk_scorer(state: ComplianceState) -> str:
    """Routing function extracted for independent unit testing."""
    threshold = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.7"))
    risk = state.get("risk_result")
    if risk is None:
        return "human_review"
    if risk.verdict in ("rejected", "needs_review"):
        return "human_review"
    if risk.confidence < threshold:
        return "human_review"
    return "report_generator"


def human_review(state: ComplianceState) -> dict:
    """Passthrough stub — replaced with interrupt() in Phase 4."""
    return {}


def _build_graph():
    builder = StateGraph(ComplianceState)

    builder.add_node("document_extractor", extract_documents)
    builder.add_node("sanctions_screener", screen_sanctions)
    builder.add_node("policy_checker", check_policy)
    builder.add_node("consistency_checker", check_consistency)
    builder.add_node("risk_scorer", score_risk)
    builder.add_node("human_review", human_review)
    builder.add_node("report_generator", generate_report)

    # Linear start
    builder.add_edge(START, "document_extractor")

    # Parallel fan-out
    builder.add_edge("document_extractor", "sanctions_screener")
    builder.add_edge("document_extractor", "policy_checker")
    builder.add_edge("document_extractor", "consistency_checker")

    # Fan-in to risk scorer
    builder.add_edge("sanctions_screener", "risk_scorer")
    builder.add_edge("policy_checker", "risk_scorer")
    builder.add_edge("consistency_checker", "risk_scorer")

    # Conditional routing after risk scorer
    builder.add_conditional_edges(
        "risk_scorer",
        route_after_risk_scorer,
        {"human_review": "human_review", "report_generator": "report_generator"},
    )

    builder.add_edge("human_review", "report_generator")
    builder.add_edge("report_generator", END)

    return builder.compile(checkpointer=MemorySaver())


graph = _build_graph()


def run_graph(
    document_paths: list[str],
    policy_path: str | None,
    thread_id: str,
) -> ComplianceState:
    initial_state: ComplianceState = {
        "document_paths": document_paths,
        "policy_path": policy_path,
        "document_data": None,
        "sanctions_result": None,
        "policy_result": None,
        "consistency_result": None,
        "risk_result": None,
        "compliance_report": None,
        "human_decision": None,
        "errors": [],
        "thread_id": thread_id,
    }
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke(initial_state, config=config)
