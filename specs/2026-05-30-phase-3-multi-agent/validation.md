# Validation — Phase 3: Full Multi-Agent System

Phase 3 is ready to merge when all unit tests pass.

---

## 1. Unit Tests

```bash
pytest tests/unit/ -m unit -v
```

All Phase 1 and Phase 2 tests must continue to pass. The following new tests must also pass:

| Test file | Key assertions |
|---|---|
| `tests/unit/agents/test_sanctions_screener.py` | Sanctioned entity → `is_clear=False`; clean document → `is_clear=True`; LLM exception → `confidence=0.0` + error appended; node only returns its own keys |
| `tests/unit/agents/test_policy_checker.py` | Policy violation found → `is_clear=False`; clean document → `is_clear=True`; LLM exception → `confidence=0.0` + error appended; node only returns its own keys |
| `tests/unit/agents/test_consistency_checker.py` | Inconsistent amounts → discrepancy in list; consistent document → `is_clear=True`; LLM exception → `confidence=0.0` + error appended; node only returns its own keys |
| `tests/unit/agents/test_risk_scorer.py` | All clear + high confidence → verdict `"clear"`; any `is_clear=False` → `"needs_review"`; critical sanctions hit → `"rejected"`; node only returns its own keys |
| `tests/unit/agents/test_report_generator.py` | Full clean state → `ComplianceReport` with verdict `"clear"`; human decision present → included in report; LLM exception → error appended; node only returns its own keys |
| `tests/unit/workflow/test_routing.py` | All 4 routing conditions return the correct next node |

---

## Merge Checklist

- [ ] `pytest tests/unit/ -m unit -v` — all tests pass (38 from Phases 1–2 + new Phase 3 tests)
- [ ] No real API calls made during `pytest` (LLM mocked in all agent tests; risk scorer has no LLM call)
- [ ] `human_review` node exists in the graph as a passthrough stub
- [ ] `run_graph()` signature is unchanged from Phase 2 (`main.py` requires no edits)
- [ ] Routing function is a standalone Python function (not inlined in graph builder) — required for unit testability
- [ ] `CONFIDENCE_THRESHOLD` is read from env var, not hard-coded

---

## Post-merge smoke test (optional, requires API keys)

```bash
python main.py tests/fixtures/sample_invoice.txt
python main.py tests/fixtures/sample_flagged_invoice.txt
```

Expected for clean invoice: `compliance_report.verdict == "clear"` or routes to human review if confidence < 0.7.
Expected for flagged invoice: `compliance_report.verdict == "needs_review"` or `"rejected"` — sanctions screener should surface the Zarkon Trading Corporation hit.
