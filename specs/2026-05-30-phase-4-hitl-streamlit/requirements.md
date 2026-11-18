# Requirements — Phase 4: Human-in-the-Loop + Streamlit UI

## Scope

Replace the `human_review` passthrough stub with a real LangGraph `interrupt()`, and build the complete single-file Streamlit app that drives the full compliance workflow from a browser.

### In scope

| Deliverable | File | Notes |
|---|---|---|
| HITL workflow | `app/graph/workflow.py` (updated) | `interrupt()` in human_review node; `Command(resume=...)` resumes |
| Shared state store | `app/state_store.py` | Module-level dict; get/set/clear helpers |
| Background thread runner | `app/runner.py` | Daemon threads; handles interrupt and completion |
| Streamlit app | `streamlit_app.py` | All 5 views; single file; no separate backend |
| HITL integration test | `tests/integration/test_graph_hitl.py` | interrupt fires; Command(resume) resumes correctly |
| State store unit tests | `tests/unit/test_state_store.py` | get/set/clear contract |
| UI tests | `tests/ui/test_streamlit_app.py` | AppTest for all 5 views; mocked graph |

### Out of scope

- User authentication or role-based access control
- Persistent storage (sessions live only in memory for the process lifetime)
- File storage beyond saving uploads to `UPLOAD_DIR` for the graph to read
- Multi-user concurrency hardening beyond what `threading.Thread` + a module-level dict provides
- LangSmith evaluation (Phase 5)

---

## Decisions

### Shared state mechanism
Use a module-level dict (`_sessions`) in `app/state_store.py`. This is the simplest correct approach for a single-server demo: it is thread-safe for reads and individual key writes in CPython due to the GIL, and the roadmap explicitly calls out "thread-safe for single-server demo" as the requirement. No `st.cache_resource`, no Redis.

### Background thread contract
Each graph run (initial and resume) is a separate daemon thread. The thread updates `_sessions` directly. Streamlit polls by calling `st.rerun()` every 2 s while `status == "processing"`. The `session_id` is a UUID stored in `st.session_state` on first render and persists across reruns within the same browser session.

After a graph run, the thread inspects `graph.get_state(config).next` rather than catching an exception to determine whether the graph paused at `human_review`. If `.next` is non-empty the thread writes `status="awaiting_review"` and extracts the interrupt payload via task interrupts; otherwise it writes `status="completed"` with the final state.

### interrupt() data
`interrupt()` is called with the `RiskResult` dict as the interrupt value. The Streamlit review view reads `interrupt_data` from the session store to populate the findings display. When the officer submits a decision, `resume_review()` calls `Command(resume=decision_string)`.

**Important — LangGraph 0.2.57 behaviour:** `interrupt()` does NOT raise `GraphInterrupt` to the caller of `graph.invoke()`. Instead, `invoke()` returns normally with the partial state at the checkpoint, and the graph is persisted as paused. Detect a pause by checking `graph.get_state(config).next` — a non-empty tuple means the graph is waiting at the named node(s). `app/runner.py` uses this check; `pytest.raises(GraphInterrupt)` cannot be used in integration tests.

### Parallel-write safety on `errors` field
`ComplianceState.errors` must be declared as `Annotated[list[str], operator.add]` (not a plain `list[str]`). The three parallel agents (sanctions_screener, policy_checker, consistency_checker) all write to the `errors` field in the same LangGraph execution step when they fail. LangGraph's default `LastValue` channel only accepts one writer per step and raises `InvalidUpdateError` otherwise. The `operator.add` reducer tells LangGraph to concatenate the lists from all parallel writers.

### File handling
Uploaded files are written to `UPLOAD_DIR` (from env, default `./uploads`) before the graph thread starts. The graph reads them from disk via `pdf_reader`. Files are not cleaned up automatically in Phase 4 (cleanup is out of scope for the demo).

### Input validation
Enforced in the Streamlit UI before the thread is started, per tech-stack.md:
- File extension must be `.pdf`
- File size must be ≤ `MAX_FILE_SIZE_MB`
- At least one trade document must be uploaded
The graph never receives invalid input.

### `run_graph()` signature change
Phase 4 adds an optional `resume_command` parameter to `run_graph()`. The default is `None` (initial run). `main.py` is unaffected since it always calls with the default. This is the only change to the public interface of `workflow.py`.

---

## Context

Phase 4 completes the v1 success criterion from `mission.md`:
> "A compliance officer uploads PDFs via a web interface, all agents run and produce findings, a flagged case pauses for human review and accepts the officer's decision, a compliance report is generated with the final verdict and supporting evidence."

The Streamlit app is the only user-facing interface in v1. It must degrade gracefully: if anything goes wrong in the background thread, the UI shows the error view with a restart option — no raw tracebacks, no PII in error messages.

The `human_review` node interrupt fires only when the risk scorer routes to it (rejected, needs_review, or low confidence). Clear + high-confidence cases bypass human review and go directly to the report generator — the interrupt never fires for those cases, and the UI transitions directly from processing to completed.
