"""
Background thread runner for the compliance graph.

Each graph run (initial and resume) is a daemon thread so the Streamlit
process doesn't block waiting for LLM calls to complete.
"""
import threading

from langgraph.types import Command

from app import state_store
from app.graph import workflow
from app.utils.logging import get_logger

logger = get_logger(__name__)


def run_in_background(
    session_id: str,
    document_paths: list[str],
    policy_path: str | None,
) -> None:
    """Start a daemon thread that runs the full compliance graph."""
    thread_id = session_id

    def _run() -> None:
        state_store.set_session(session_id, status="processing", thread_id=thread_id)
        try:
            partial_state = workflow.run_graph(document_paths, policy_path, thread_id)
            config = {"configurable": {"thread_id": thread_id}}
            graph_state = workflow.graph.get_state(config)

            if graph_state.next:
                # Graph paused at human_review — extract interrupt payload
                interrupt_data = _extract_interrupt_data(graph_state)
                state_store.set_session(
                    session_id,
                    status="awaiting_review",
                    interrupt_data=interrupt_data,
                )
            else:
                state_store.set_session(session_id, status="completed", final_state=partial_state)
        except Exception as exc:
            logger.error("runner_failed", error_type=type(exc).__name__)
            state_store.set_session(session_id, status="error", error="Processing failed.")

    threading.Thread(target=_run, daemon=True).start()


def resume_review(session_id: str, decision: str, thread_id: str) -> None:
    """Start a daemon thread that resumes the graph after human review."""

    def _resume() -> None:
        state_store.set_session(session_id, status="processing")
        try:
            final_state = workflow.run_graph(
                document_paths=[],
                policy_path=None,
                thread_id=thread_id,
                resume_command=Command(resume=decision),
            )
            state_store.set_session(session_id, status="completed", final_state=final_state)
        except Exception as exc:
            logger.error("resume_failed", error_type=type(exc).__name__)
            state_store.set_session(session_id, status="error", error="Resume failed.")

    threading.Thread(target=_resume, daemon=True).start()


def _extract_interrupt_data(graph_state) -> dict:
    """Pull the interrupt payload out of a paused graph state."""
    for task in getattr(graph_state, "tasks", []):
        for intr in getattr(task, "interrupts", []):
            v = getattr(intr, "value", {})
            return v if isinstance(v, dict) else {}
    return {}
