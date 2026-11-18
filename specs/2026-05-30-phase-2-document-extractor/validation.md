# Validation — Phase 2: Single-Agent Pipeline

Phase 2 is ready to merge when both checks below pass. LangSmith trace confirmation is not required for merge.

---

## 1. Unit Tests

```bash
pytest tests/unit/ -m unit -v
```

All 33 Phase 1 tests must continue to pass. The following new tests must also pass:

| Test file | Key assertions |
|---|---|
| `tests/unit/agents/test_document_extractor.py` | Valid mocked LLM response → `document_data` is a `DocumentData` instance with `extraction_confidence > 0`; LLM exception → `extraction_confidence == 0.0` and `"document_extractor_failed"` in `state["errors"]`; node does not overwrite unrelated state fields |

---

## 2. Integration Tests

```bash
pytest tests/integration/ -v
```

| Test file | Key assertions |
|---|---|
| `tests/integration/test_graph_routing.py` | Graph runs start-to-end with mocked extractor; final state has populated `document_data`; graph runs with simulated LLM failure; final state has `"document_extractor_failed"` in `errors` |

---

## Merge Checklist

- [ ] `pytest tests/unit/ -m unit -v` — all tests pass (including 33 from Phase 1)
- [ ] `pytest tests/integration/ -v` — all integration tests pass
- [ ] No real API calls made during `pytest` (LLM is mocked in all tests)
- [ ] `LANGCHAIN_TRACING_V2=false` is set in the test environment (confirmed in `conftest.py`)
- [ ] `main.py` exists and accepts a PDF path argument (`python main.py --help` works without error)
- [ ] `app/agents/document_extractor.py` contains no hardcoded model name (reads from `COMPLIANCE_MODEL` env var)
- [ ] No unhandled exceptions propagate out of the extractor node — all failures set `extraction_confidence=0.0` and append to `errors`

---

## Post-merge smoke test (optional, requires API keys)

Once API keys are available:

```bash
python main.py tests/fixtures/sample_invoice.pdf
```

Expected: prints a `DocumentData` JSON object with recognisable fields from the sample invoice. Run appears in LangSmith UI under project `trade-finance-compliance`.

```bash
python main.py tests/fixtures/sample_flagged_invoice.pdf
```

Expected: prints a `DocumentData` JSON object. `buyer` or `seller` field contains the sanctioned entity name from the flagged fixture (extraction only — no sanctions check yet).
