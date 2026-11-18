import pytest
import app.state_store as ss
from app.state_store import clear_session, get_session, set_session


@pytest.fixture(autouse=True)
def clean_store():
    ss._sessions.clear()
    yield
    ss._sessions.clear()


@pytest.mark.unit
def test_get_session_unknown_id_returns_default():
    result = get_session("unknown-id")
    assert result["status"] == "idle"
    assert result["interrupt_data"] is None
    assert result["final_state"] is None
    assert result["error"] is None


@pytest.mark.unit
def test_set_session_creates_entry_and_sets_field():
    set_session("sess-1", status="processing")
    result = get_session("sess-1")
    assert result["status"] == "processing"


@pytest.mark.unit
def test_set_session_merges_without_overwriting_unrelated_keys():
    set_session("sess-2", status="processing", final_state={"x": 1})
    set_session("sess-2", status="completed")
    result = get_session("sess-2")
    assert result["status"] == "completed"
    assert result["final_state"] == {"x": 1}


@pytest.mark.unit
def test_clear_session_removes_entry():
    set_session("sess-3", status="error", error="Something failed.")
    clear_session("sess-3")
    result = get_session("sess-3")
    assert result["status"] == "idle"
    assert result["error"] is None


@pytest.mark.unit
def test_clear_session_on_unknown_id_is_a_no_op():
    clear_session("does-not-exist")
    assert get_session("does-not-exist")["status"] == "idle"
