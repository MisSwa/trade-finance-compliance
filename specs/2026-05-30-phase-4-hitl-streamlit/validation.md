# Validation — Phase 4: Human-in-the-Loop + Streamlit UI

Phase 4 is ready to merge when all automated tests pass. Manual browser demo is deferred until API keys are available.

---

## 1. Unit Tests

```bash
pytest tests/unit/ -m unit -v
```

All 67 tests from Phases 1–3 must continue to pass. New tests that must pass:

| Test file | Key assertions |
|---|---|
| `tests/unit/test_state_store.py` | `get_session` on unknown ID returns default; `set_session` merges without overwriting; `clear_session` removes entry |

---

## 2. Integration Tests

```bash
pytest tests/integration/ -v
```

| Test file | Key assertions |
|---|---|
| `tests/integration/test_graph_hitl.py` | Graph pauses at `human_review` when verdict is `"needs_review"`; `Command(resume="approve")` unblocks and produces a `compliance_report`; `human_decision` is set correctly in final state |

---

## 3. UI Tests

```bash
pytest tests/ui/ -v
```

| Test | What it checks |
|---|---|
| `test_upload_view_renders` | App starts idle; file uploader and submit button present |
| `test_submit_blocked_without_files` | Submit without files shows error; status stays idle |
| `test_processing_view_shown` | Pre-set `status="processing"` renders spinner |
| `test_review_view_renders` | Pre-set `status="awaiting_review"` renders decision radio and confirm button |
| `test_decision_submit` | Selecting decision and clicking confirm updates session state |
| `test_report_view_renders` | Pre-set `status="completed"` renders report and download button |
| `test_error_view_renders` | Pre-set `status="error"` renders error message and restart button |
| `test_restart_clears_session` | Clicking restart resets status to idle |

---

## Merge Checklist

- [ ] `pytest tests/unit/ -m unit -v` — all 67+ tests pass
- [ ] `pytest tests/integration/ -v` — HITL interrupt and resume tests pass
- [ ] `pytest tests/ui/ -v` — all 8 AppTest UI tests pass
- [ ] No real API calls in any test (graph mocked in HITL and UI tests)
- [ ] `streamlit_app.py --help` equivalent: `python -c "import streamlit_app"` imports without error
- [ ] `run_graph()` still accepts calls without `resume_command` — `main.py` unaffected
- [ ] No PII in error view — error messages use generic strings only
- [ ] `UPLOAD_DIR` is created if it does not exist (app does not crash on first run)

---

## Post-merge smoke test (optional, requires API keys)

```bash
streamlit run streamlit_app.py
```

1. Upload `tests/fixtures/sample_invoice.txt` (rename to `.pdf` for the uploader, or use a real PDF)
2. Confirm processing spinner appears
3. For a flagged document: confirm review view appears with findings; submit a decision
4. Confirm completed view renders with full report and download button
5. Confirm restart returns to idle view
