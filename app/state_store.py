"""
Shared in-memory session state store.

Keyed by session_id (UUID string). Each entry holds the fields
the background thread writes and the Streamlit app reads.

Thread-safe for individual key reads/writes under CPython's GIL,
which is sufficient for the single-server demo requirement.
"""

_DEFAULT: dict = {
    "status": "idle",
    "interrupt_data": None,
    "final_state": None,
    "error": None,
    "thread_id": None,
}

_sessions: dict[str, dict] = {}


def get_session(session_id: str) -> dict:
    """Return session dict, or a fresh default if the session doesn't exist."""
    return _sessions.get(session_id, dict(_DEFAULT))


def set_session(session_id: str, **kwargs) -> None:
    """Merge kwargs into the session entry, creating it if necessary."""
    if session_id not in _sessions:
        _sessions[session_id] = dict(_DEFAULT)
    _sessions[session_id].update(kwargs)


def clear_session(session_id: str) -> None:
    """Remove the session entry entirely."""
    _sessions.pop(session_id, None)
