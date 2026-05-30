# Roadmap

Each phase delivers a working, testable capability milestone. Later phases build on earlier ones without requiring rewrites.

---

## Phase 1 — Foundation

**Goal:** Everything compiles, environment is wired up, and core data contracts are defined. No LLM calls yet.

**Deliverables:**

- `requirements.txt` with pinned dependencies
- `.env.example` with all required keys documented
- `app/models/schemas.py` — all Pydantic models and the `ComplianceState` TypedDict used across every agent and the graph
- `app/tools/pdf_reader.py` — PDF text extraction via `pypdf`; graceful handling of unreadable/scanned PDFs
- `app/tools/watchlist.py` — mock sanctions data: sanctioned companies, vessels, high-risk countries, high-risk ports, prohibited goods categories
- `app/utils/logging.py` — `structlog`-based privacy-aware logger; `mask_sensitive_field()` helper

**Done when:** `python -c "from app.models.schemas import ComplianceState; print('ok')"` runs without errors.

---

## Phase 2 — Single-Agent Pipeline (Document Extractor)

**Goal:** One LLM call, one structured output, LangSmith tracing working end-to-end.

**Deliverables:**

- `app/agents/document_extractor.py` — LangGraph node that takes `document_paths`, reads PDFs, and uses Claude with `with_structured_output(DocumentData)` to extract: buyer, seller, goods description, amounts, currency, country of origin, port of loading/discharge, vessel name, date, doc type
- Minimal `app/graph/workflow.py` — single-node graph (extractor only) with `MemorySaver` checkpointer
- `main.py` (CLI mode) — accepts a PDF path, runs the single-node graph, prints extracted JSON
- LangSmith tracing confirmed: run appears in LangSmith UI with correct project name

**Done when:** Uploading a sample invoice PDF produces a correctly populated `DocumentData` object and the run appears in LangSmith.

---

## Phase 3 — Full Multi-Agent System

**Goal:** All six agents running, parallel execution working, risk verdict produced.

**Deliverables:**

- `app/agents/sanctions_screener.py` — checks extracted entity names, vessel, ports, and country of origin against the mock watchlist; returns `SanctionsResult` with hit list, severity, and confidence
- `app/agents/policy_checker.py` — given extracted document data and optional policy PDF text, uses Claude to identify violations of bank policy rules; returns `PolicyResult`
- `app/agents/consistency_checker.py` — cross-checks field values across all documents (e.g. invoice amount vs. BoL goods, country of origin consistency); returns `ConsistencyResult` with discrepancies
- `app/agents/risk_scorer.py` — aggregates findings from the three parallel agents; produces a `RiskResult` with numeric score (0–1), verdict (`clear` / `needs_review` / `rejected`), confidence score, and weighted risk factors
- `app/agents/report_generator.py` — produces the final `ComplianceReport` with full reasoning, regulatory recommendations, and whether SAR consideration is warranted
- `app/graph/workflow.py` (updated) — full graph: extractor → [sanctions + policy + consistency in parallel] → risk scorer → conditional routing → report generator

**Routing logic:**
- `verdict == "rejected"` → always human review
- `verdict == "needs_review"` → always human review
- `confidence < CONFIDENCE_THRESHOLD (0.7)` → human review even if verdict is "clear"
- `verdict == "clear"` AND `confidence >= 0.7` → skip to report generator

**Done when:** Running three sample documents (clear, flagged, inconsistent) each produces the correct verdict with supporting reasoning, all visible in LangSmith traces.

---

## Phase 4 — Human-in-the-Loop + Streamlit UI

**Goal:** A compliance officer can upload documents in a browser, review flagged cases, and receive a final report — without touching the command line.

**Deliverables:**

- `app/graph/workflow.py` (updated) — `interrupt()` call inside `human_review` node; graph pauses and checkpoints state; resumes via `Command(resume=decision)`
- `streamlit_app.py` — single Streamlit app file; all UI views are rendered conditionally based on `st.session_state.status`:

  | Status value | View rendered |
  |---|---|
  | `idle` | Upload view — `st.file_uploader` for trade docs + optional policy PDF; submit button starts background thread |
  | `processing` | Progress view — spinner with live status messages; `st.rerun()` polls the thread every 2 s |
  | `awaiting_review` | Review view — risk score, verdict badge, agent findings (sanctions hits, policy violations, discrepancies); decision radio (`Approve / Reject / Escalate`) + notes text area + confirm button |
  | `completed` | Report view — full compliance report with verdict, risk factors, regulatory actions, audit summary; download button for report text |
  | `error` | Error view — generic failure message (no PII); option to restart |

- Background thread contract: stores `{ status, interrupt_data, final_state, error }` in a shared dict keyed by `session_id` (UUID stored in `st.session_state`); Streamlit reads this dict on each rerun

**Done when:** Full browser-based demo works on `localhost:8501` with sample documents including a human review step; `streamlit run streamlit_app.py` is the only command needed.

---

## Phase 5 — LangSmith Evaluation + Hardening

**Goal:** System quality is measurable. Failure modes are handled gracefully.

**Deliverables:**

- LangSmith evaluation dataset: labelled sample cases with expected verdicts (`clear`, `needs_review`, `rejected`)
- LangSmith custom evaluator: checks if `compliance_report.verdict` matches expected label
- Evaluation run script (`scripts/run_eval.py`) — runs dataset through the graph and reports accuracy to LangSmith
- Low-confidence hardening: if extracted document text is < 100 characters (likely unreadable PDF), the extractor returns a `DocumentData` with `extraction_confidence=0.0` and the system immediately routes to human review with a clear explanation
- Error boundary: any unhandled agent exception is caught, logged (without PII), and routes to human review rather than crashing
- README update: setup instructions, how to run demo, how to view LangSmith traces, how to run evaluation

**Done when:** Evaluation script runs against the labelled dataset and reports accuracy in the LangSmith UI. All known failure modes (unreadable PDF, agent error, low confidence) gracefully escalate to human review.

---

## Phase Summary

| Phase | Milestone | Key files |
|---|---|---|
| 1 | Foundation — schemas, tools, logging | `schemas.py`, `pdf_reader.py`, `watchlist.py`, `logging.py` |
| 2 | Single-agent pipeline + LangSmith wired | `document_extractor.py`, `workflow.py` (minimal), `main.py` |
| 3 | Full multi-agent + risk verdict | All 4 remaining agents, full `workflow.py` |
| 4 | HITL + Streamlit UI | `streamlit_app.py`, updated `workflow.py` |
| 5 | Evaluation + hardening | `scripts/run_eval.py`, error handling, README |
