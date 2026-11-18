# Phase 5 — LangSmith Evaluation + Hardening: Validation

## How to know this phase is done

All three tiers must pass before merging into `main`.

---

## Tier 1 — Unit Tests

Run:

```
pytest tests/unit/ -v
```

Expected: all tests pass with no real API calls.

### New tests added in Phase 5

| Test file | Tests | What they verify |
|---|---|---|
| `tests/unit/test_eval_runner.py` | `test_verdict_evaluator_match` | `verdict_evaluator()` returns `score: 1` when run output verdict equals the example label |
| `tests/unit/test_eval_runner.py` | `test_verdict_evaluator_mismatch` | `verdict_evaluator()` returns `score: 0` on mismatch |
| `tests/unit/test_eval_runner.py` | `test_dry_run_all_cases_pass` | All three fixture cases produce the correct verdict with mocked LLM; no LangSmith or Anthropic API calls |
| `tests/unit/test_hardening.py` | `test_unreadable_pdf_routes_to_human_review` | Extractor receives < 100 chars; sets `extraction_confidence=0.0`; `state["errors"]` is non-empty; graph routes to `human_review` |
| `tests/unit/test_hardening.py` | `test_agent_exception_routes_to_human_review` | Mocked agent raises `RuntimeError`; graph reaches `human_review` without crashing; `state["errors"]` is non-empty |

### Cumulative test count

Phase 5 must not reduce the passing count from Phase 4. Expected baseline from Phase 4: 72+ tests. Phase 5 adds at least 5 new tests.

```
pytest tests/unit/ --tb=short -q
# Must end with: X passed, 0 failed, 0 errors
```

---

## Tier 2 — Evaluation Dry-Run

Run:

```
LANGCHAIN_TRACING_V2=false python scripts/run_eval.py --dry-run
```

Expected output:

```
Running evaluation in dry-run mode (no LangSmith API calls)...
Case A (clear): PASS
Case B (rejected): PASS
Case C (needs_review): PASS
Evaluation complete. Accuracy: 3/3 cases matched.
```

Exit code must be 0. If any case fails, the script prints the failing case IDs and exits with code 1.

---

## Tier 3 — Integration Tests

Run:

```
pytest tests/integration/ -v
```

Expected: all Phase 3 and Phase 4 integration tests continue to pass. No new integration tests are required in Phase 5 — the dry-run script covers the evaluation path.

---

## Merge Checklist

Before opening a pull request to `main`, confirm each item:

- [ ] `pytest tests/unit/ -q` passes with 0 failures and 0 errors
- [ ] `pytest tests/integration/ -q` passes with 0 failures and 0 errors
- [ ] `LANGCHAIN_TRACING_V2=false python scripts/run_eval.py --dry-run` exits 0 and prints `3/3 cases matched`
- [ ] `scripts/run_eval.py` accepts `--dry-run` flag; omitting the flag triggers live mode (does not crash if `LANGCHAIN_API_KEY` is unset — prints a clear error message instead)
- [ ] `app/agents/document_extractor.py` skips the LLM call when total extracted text < 100 chars; sets `extraction_confidence=0.0`
- [ ] All five agent nodes (`document_extractor`, `sanctions_screener`, `policy_checker`, `consistency_checker`, `report_generator`) have a `try/except Exception` block that logs a privacy-safe message and returns `confidence=0.0`
- [ ] No agent exception propagates to the top-level caller — graph always routes to `human_review` or `report_generator`, never crashes
- [ ] `run_graph()` signature is unchanged (backward compatible with `main.py` and `streamlit_app.py`)
- [ ] `README.md` contains all required sections: Overview, Setup, Running the demo, CLI mode, Viewing LangSmith traces, Running tests, Running evaluation, Architecture
- [ ] No new `print()` statements in agent or graph code (use `structlog` logger)
- [ ] No PII (entity names, amounts, account numbers) appears in any log message produced by the hardening error handlers

---

## Post-Merge Smoke Test (optional but recommended)

With real API keys configured in `.env`:

```bash
# Confirm live eval uploads to LangSmith
python scripts/run_eval.py

# Confirm full demo still works after hardening changes
streamlit run streamlit_app.py
```

In LangSmith UI: navigate to Datasets → `trade-finance-compliance-v1` → Experiments. Confirm the evaluation run appears with 3/3 examples and correct scores.
