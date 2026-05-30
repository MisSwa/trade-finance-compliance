from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.agents.document_extractor import extract_documents
from app.models.schemas import ComplianceState


def _build_graph():
    builder = StateGraph(ComplianceState)
    builder.add_node("document_extractor", extract_documents)
    builder.add_edge(START, "document_extractor")
    builder.add_edge("document_extractor", END)
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
