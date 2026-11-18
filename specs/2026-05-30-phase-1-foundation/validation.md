# Validation — Phase 1: Foundation

Phase 1 is ready to merge when all three checks below pass.

---

## 1. Import Check (Roadmap criterion)

```bash
python -c "from app.models.schemas import ComplianceState; print('ok')"
```

Expected output: `ok` with no errors, warnings, or missing-module tracebacks.

---

## 2. Pytest Unit Tests

```bash
pytest tests/unit/ -m unit -v
```

All tests must pass. No skips on tests that should run (skips are only acceptable for tests explicitly marked `llm`).

**Tests that must exist and pass:**

| Test file | Key assertions |
|---|---|
| `tests/unit/models/test_schemas.py` | `ComplianceState` can be constructed as a plain dict; `RiskResult.verdict` rejects values outside `Literal["clear","needs_review","rejected"]`; all required Pydantic fields raise `ValidationError` when omitted |
| `tests/unit/tools/test_pdf_reader.py` | Valid PDF path returns a non-empty string; missing file path returns `""`; non-PDF path returns `""` without raising |
| `tests/unit/tools/test_watchlist.py` | Known sanctioned entity returns `hit=True`; unknown entity returns `hit=False`; lookup is case-insensitive; high-risk country returns expected result |
| `tests/unit/` (logging) | `mask_sensitive_field("SomeValue")` returns a string starting with `[ENTITY:`; calling it twice with the same input returns the same output; the original value does not appear in the output |

---

## 3. Manual Smoke Tests

Run these by hand before opening the PR.

### 3a. PDF extraction

Place any readable PDF on disk (e.g. a sample invoice), then:

```bash
python -c "
from app.tools.pdf_reader import extract_text
text = extract_text('path/to/sample.pdf')
print(f'Extracted {len(text)} chars')
print(text[:200])
"
```

Expected: prints character count > 100 and a readable text preview.

### 3b. Watchlist lookup

```bash
python -c "
from app.tools.watchlist import check_entity, check_country
print(check_entity('Acme Sanctioned Trading Co'))   # should show hit=True
print(check_entity('Legitimate Imports Ltd'))        # should show hit=False
print(check_country('Ruritania'))                    # should show high-risk=True
"
```

Adjust entity and country names to match whatever is in the mock dataset.

### 3c. Logging — no PII in output

```bash
python -c "
from app.utils.logging import get_logger, mask_sensitive_field
log = get_logger('smoke-test')
entity = 'Acme Sanctioned Trading Co'
log.info('sanctions_check', entity_ref=mask_sensitive_field(entity), hit=True)
"
```

Expected: JSON log line contains `entity_ref` with a hash value like `[ENTITY:a3f2c1d4]`; the string `Acme Sanctioned Trading Co` does not appear anywhere in the output.

---

## Merge Checklist

- [ ] `python -c "from app.models.schemas import ComplianceState; print('ok')"` passes
- [ ] `pytest tests/unit/ -v` — all tests pass, no unexpected skips
- [ ] Smoke test 3a: PDF extraction returns > 100 characters
- [ ] Smoke test 3b: Known sanctioned entity returns `hit=True`; unknown returns `hit=False`
- [ ] Smoke test 3c: Log output contains masked hash, not raw entity name
- [ ] No LLM imports (`langchain_anthropic`, `langgraph`) appear in Phase 1 source files
- [ ] `.env.example` documents all keys from tech-stack.md
- [ ] `requirements.txt` uses pinned `==` versions for all direct dependencies
