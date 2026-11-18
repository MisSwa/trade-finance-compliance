# Plan — Phase 4: Human-in-the-Loop + Streamlit UI

Each task group is independently completable. Within a group, tasks are ordered by dependency.

---

## Group 1 — HITL Workflow

1. Update `app/graph/workflow.py` — replace the `human_review` passthrough stub with a real interrupt node:
   - Call `interrupt(state["risk_result"])` inside `human_review` to pause the graph and surface findings to the UI
   - Resume path: accept `Command(resume=decision)` where `decision` is `"approve"`, `"reject"`, or `"escalate"`; write the decision into `state["human_decision"]` and continue to `report_generator`
   - Update `run_graph()` to accept an optional `resume_command: Command | None` parameter; when provided, invoke the graph with the command instead of initial state

2. Add `tests/integration/test_graph_hitl.py`:
   - Test: graph pauses at `human_review` node when verdict is `"needs_review"` — after `run_graph()` returns, `graph.get_state(config).next` contains `"human_review"` (LangGraph 0.2.57: `interrupt()` does NOT raise `GraphInterrupt` to the `invoke()` caller; the partial state is checkpointed and `invoke()` returns normally)
   - Test: `Command(resume="approve")` unblocks the graph; final state has `human_decision == "approve"` and a populated `compliance_report`
   - Test: `Command(resume="reject")` unblocks the graph; final state has `human_decision == "reject"`
   - All tests must mock **all five LLM agents** (document_extractor, sanctions_screener, policy_checker, consistency_checker, report_generator); mocking only the extractor is insufficient — unmocked parallel agents fail with confidence=0.0 → risk_scorer routes to human_review even in non-HITL tests

## Group 2 — Shared State Contract

3. Create `app/state_store.py`:
   - Module-level dict `_sessions: dict[str, dict]` — the shared state store
   - Each entry keyed by `session_id` (UUID string); value is `{ "status", "interrupt_data", "final_state", "error" }`
   - `get_session(session_id) -> dict` — returns entry or a default idle dict
   - `set_session(session_id, **kwargs)` — merges kwargs into the session entry
   - `clear_session(session_id)` — removes the entry (used on restart)
   - Status values mirror Streamlit view names: `"idle"`, `"processing"`, `"awaiting_review"`, `"completed"`, `"error"`

4. Add `tests/unit/test_state_store.py`:
   - Test: `get_session` on unknown ID returns default idle dict
   - Test: `set_session` merges fields without overwriting unrelated keys
   - Test: `clear_session` removes the entry; subsequent `get_session` returns default

## Group 3 — Background Thread Runner

5. Create `app/runner.py`:
   - `run_in_background(session_id, document_paths, policy_path)` — starts a `threading.Thread` (daemon=True) that:
     1. Sets session status to `"processing"`
     2. Calls `workflow.run_graph()` with a new `thread_id`
     3. If the graph raises `GraphInterrupt`: sets status to `"awaiting_review"`, stores `interrupt_data`
     4. If the graph completes normally: sets status to `"completed"`, stores `final_state`
     5. On any unhandled exception: sets status to `"error"`, stores sanitised error message (no PII)
   - `resume_review(session_id, decision)` — starts a new daemon thread that calls `workflow.run_graph()` with `Command(resume=decision)` and updates session to `"completed"` or `"error"`

## Group 4 — Streamlit App

6. Create `streamlit_app.py` at project root — single file; all views rendered conditionally on `st.session_state.status`:

   **idle view** (`status == "idle"` or missing):
   - `st.file_uploader` for trade docs (multi-file, PDF only)
   - Optional `st.file_uploader` for policy PDF
   - Submit button: validates files, saves to `UPLOAD_DIR`, sets `session_id`, calls `run_in_background()`, sets status to `"processing"`
   - Inline validation errors for wrong file type, oversized file, no file selected

   **processing view** (`status == "processing"`):
   - Spinner with status message
   - `st.rerun()` polls every 2 s until status changes

   **awaiting_review view** (`status == "awaiting_review"`):
   - Displays risk score, verdict badge, sanctions hits, policy violations, discrepancies from `interrupt_data`
   - Decision radio: `Approve / Reject / Escalate`
   - Notes text area
   - Confirm button: calls `resume_review(session_id, decision)`, sets status back to `"processing"`

   **completed view** (`status == "completed"`):
   - Full compliance report: verdict, risk factors, recommendations, SAR flag, reasoning, audit summary
   - Download button for report as plain text
   - Restart button resets session

   **error view** (`status == "error"`):
   - Generic failure message (no PII)
   - Restart button resets session

7. Add `tests/ui/test_streamlit_app.py` using `streamlit.testing.v1.AppTest`:
   - `test_upload_view_renders`: app starts in idle state; file uploader and submit button present
   - `test_submit_blocked_without_files`: submit without files shows error, status stays idle
   - `test_processing_view_shown`: pre-set `status="processing"` renders spinner
   - `test_review_view_renders`: pre-set `status="awaiting_review"` with mock interrupt_data renders decision radio and confirm button
   - `test_decision_submit`: selecting decision and clicking confirm updates session state
   - `test_report_view_renders`: pre-set `status="completed"` with mock final_state renders the "Compliance Report" subheader and "Start New Review" button (`at.download_button` does not exist in Streamlit 1.35's AppTest — check `at.subheader` for report content instead)
   - `test_error_view_renders`: pre-set `status="error"` renders error message and restart button
   - `test_restart_clears_session`: clicking restart resets status to idle
