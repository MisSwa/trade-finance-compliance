# Phase 5 — LangSmith Evaluation + Hardening: Plan

## Task Groups

---

### Group 1 — LangSmith Evaluation Dataset and Evaluator

1. Create `scripts/eval_dataset.py` — programmatically builds three labelled evaluation cases from existing test fixtures:
   - Case A: clear transaction (no sanctions hits, no policy violations, no discrepancies, confidence ≥ 0.7) → expected verdict: `clear`
   - Case B: sanctioned entity hit (severity `high`, confidence ≥ 0.7) → expected verdict: `rejected`
   - Case C: document inconsistencies found (amount mismatch, confidence ≥ 0.7) → expected verdict: `needs_review`
   - Each case is a dict with keys: `case_id`, `label` (expected verdict), `document_paths`, `policy_path`; stored as a list exported from the module

2. Create `scripts/eval_runner.py` — LangSmith evaluation logic:
   - `build_dataset(client)` — creates or retrieves a LangSmith dataset named `trade-finance-compliance-v1`; uploads the three cases as examples with `inputs` and `reference_outputs`
   - `verdict_evaluator(run, example)` — custom evaluator that extracts `compliance_report.verdict` from the run output and compares it to `reference_outputs["verdict"]`; returns `{"key": "verdict_match", "score": 1}` on match, `{"key": "verdict_match", "score": 0}` on mismatch
   - `run_evaluation(dry_run=False)` — if `dry_run=True`, runs cases through the graph with mocked LLM calls and asserts verdicts match expected labels without calling LangSmith API; if `dry_run=False`, calls `evaluate()` with the real client

---

### Group 2 — Evaluation Entry-Point Script

3. Create `scripts/run_eval.py` — CLI entry point:
   - `argparse` with single flag `--dry-run` (boolean, default False)
   - Calls `run_evaluation(dry_run=args.dry_run)` from `eval_runner`
   - On success: prints `Evaluation complete. Accuracy: N/3 cases matched.`
   - On failure: prints the failing case IDs and exits with code 1
   - Ensure `scripts/__init__.py` exists so the module is importable in tests

4. Write `tests/unit/test_eval_runner.py`:
   - `test_verdict_evaluator_match` — evaluator returns score 1 when run output verdict matches label
   - `test_verdict_evaluator_mismatch` — evaluator returns score 0 on mismatch
   - `test_dry_run_all_cases_pass` — mocked graph confirms all three fixture cases produce the correct verdict (no real API calls)

---

### Group 3 — Hardening: Low-Confidence PDF and Agent Error Boundary

5. Update `app/agents/document_extractor.py` — low-confidence PDF guard:
   - After `extract_text()`, check total character count across all documents
   - If total characters < 100, skip the LLM call; set `document_data.extraction_confidence = 0.0` and append `"Unreadable PDF: text too short for reliable extraction"` to `state["errors"]`
   - Add `tests/unit/test_hardening.py`: `test_unreadable_pdf_routes_to_human_review` — fixture returns empty string from `extract_text`; assert confidence is 0.0 and `state["errors"]` is non-empty

6. Confirm per-agent error boundary in all five agent nodes (`document_extractor`, `sanctions_screener`, `policy_checker`, `consistency_checker`, `report_generator`):
   - Each node already wraps its main logic in `try/except Exception`; verify the `except` block logs a privacy-safe message (no entity names or amounts), sets the agent's result confidence to 0.0, and appends to `state["errors"]`
   - If any agent is missing this pattern, add it
   - Add `test_agent_exception_routes_to_human_review` in `test_hardening.py`: mock an agent to raise `RuntimeError`; assert the graph reaches `human_review` and does not crash

---

### Group 4 — README Update

7. Overwrite `README.md` with the following sections (replace existing content):
   - **Overview** — one paragraph describing the system and its purpose
   - **Setup** — step-by-step: clone, create venv, `pip install -r requirements.txt`, copy `.env.example` to `.env`, fill in `ANTHROPIC_API_KEY` and `LANGCHAIN_API_KEY`
   - **Running the demo** — `streamlit run streamlit_app.py`; expected flow (upload → processing → review → report)
   - **CLI mode** — `python main.py <pdf_path> [--policy <pdf_path>]`; sample output
   - **Viewing LangSmith traces** — set `LANGCHAIN_TRACING_V2=true`; link to LangSmith UI
   - **Running tests** — `pytest` to run all tests; `pytest tests/unit/` for unit only
   - **Running evaluation** — `python scripts/run_eval.py --dry-run` for local check; `python scripts/run_eval.py` for live LangSmith eval
   - **Architecture** — brief description of the six agents and the graph routing logic
