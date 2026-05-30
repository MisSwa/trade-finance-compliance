"""UI tests for streamlit_app.py using Streamlit AppTest."""
import pytest
from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest

from app.models.schemas import ComplianceReport

_APP_PATH = "streamlit_app.py"

_INTERRUPT_DATA = {
    "verdict": "needs_review",
    "score": 0.72,
    "confidence": 0.85,
    "risk_factors": ["Sanctions: Sanctioned entity found."],
}

_MOCK_REPORT = ComplianceReport(
    verdict="clear",
    risk_score=0.1,
    recommendations=["No further action required."],
    sar_warranted=False,
    reasoning="All agents returned clear with high confidence.",
    audit_summary="Transaction cleared by automated compliance review.",
)


def _run_with_status(status: str, extra: dict | None = None) -> AppTest:
    """Helper: boot the app with a pre-set session status."""
    session_data = {"status": status, **(extra or {})}
    with patch("app.state_store.get_session", return_value=session_data):
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.session_state["session_id"] = "test-session-ui"
        at.run()
    return at


@pytest.mark.unit
def test_upload_view_renders():
    at = _run_with_status("idle")
    assert any(b.label == "Run Compliance Check" for b in at.button)


@pytest.mark.unit
def test_submit_blocked_without_files():
    session_data = {"status": "idle"}
    with patch("app.state_store.get_session", return_value=session_data):
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.session_state["session_id"] = "test-session-ui"
        at.run()
        # Click submit with no files uploaded
        submit = next(b for b in at.button if b.label == "Run Compliance Check")
        with patch("app.state_store.get_session", return_value=session_data):
            submit.click().run()
    assert any("Please upload at least one trade document" in e.value for e in at.error)


@pytest.mark.unit
def test_processing_view_shown():
    with patch("time.sleep"), \
         patch("app.state_store.get_session", return_value={"status": "processing"}), \
         patch("streamlit.rerun"):
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.session_state["session_id"] = "test-session-ui"
        at.run()
    assert any("Running compliance analysis" in i.value for i in at.info)


@pytest.mark.unit
def test_review_view_renders():
    at = _run_with_status(
        "awaiting_review",
        {"interrupt_data": _INTERRUPT_DATA, "thread_id": "test-thread"},
    )
    assert any(r.label == "Decision" for r in at.radio)
    assert any(b.label == "Confirm Decision" for b in at.button)


@pytest.mark.unit
def test_decision_submit():
    session_data = {
        "status": "awaiting_review",
        "interrupt_data": _INTERRUPT_DATA,
        "thread_id": "test-thread",
    }
    mock_resume = MagicMock()
    mock_set = MagicMock()

    with patch("app.state_store.get_session", return_value=session_data), \
         patch("app.runner.resume_review", mock_resume), \
         patch("app.state_store.set_session", mock_set):
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.session_state["session_id"] = "test-session-ui"
        at.run()
        decision_radio = next(r for r in at.radio if r.label == "Decision")
        decision_radio.set_value("Reject")
        confirm = next(b for b in at.button if b.label == "Confirm Decision")
        with patch("app.state_store.get_session", return_value=session_data), \
             patch("app.runner.resume_review", mock_resume), \
             patch("app.state_store.set_session", mock_set), \
             patch("streamlit.rerun"):
            confirm.click().run()

    mock_resume.assert_called_once()
    call_args = mock_resume.call_args
    assert call_args[0][1] == "reject"  # decision argument


@pytest.mark.unit
def test_report_view_renders():
    at = _run_with_status(
        "completed",
        {"final_state": {"compliance_report": _MOCK_REPORT}},
    )
    # st.download_button is not captured by AppTest 1.35; verify report content instead
    assert any("Compliance Report" in s.value for s in at.subheader)
    assert any(b.label == "Start New Review" for b in at.button)


@pytest.mark.unit
def test_error_view_renders():
    at = _run_with_status("error")
    assert any("error occurred" in e.value.lower() for e in at.error)
    assert any(b.label == "Start New Review" for b in at.button)


@pytest.mark.unit
def test_restart_clears_session():
    mock_clear = MagicMock()
    session_data = {"status": "error"}

    with patch("app.state_store.get_session", return_value=session_data), \
         patch("app.state_store.clear_session", mock_clear), \
         patch("streamlit.rerun"):
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.session_state["session_id"] = "test-session-ui"
        at.run()
        restart = next(b for b in at.button if b.label == "Start New Review")
        with patch("app.state_store.get_session", return_value=session_data), \
             patch("app.state_store.clear_session", mock_clear), \
             patch("streamlit.rerun"):
            restart.click().run()

    mock_clear.assert_called_once_with("test-session-ui")
