# Plan — Phase 1: Foundation

Each task group below is independently completable. Within a group, tasks are ordered by dependency.

---

## Group 1 — Project Scaffold

1. Create `requirements.txt` with pinned dependencies: `langchain-anthropic`, `langgraph`, `langsmith`, `pypdf`, `pydantic`, `structlog`, `python-dotenv`, `streamlit`, `pytest`, `pytest-mock`, `pytest-asyncio`
2. Create `.env.example` with all required keys documented (see tech-stack.md configurable parameters)
3. Create the package directory structure: `app/`, `app/models/`, `app/tools/`, `app/utils/`, `app/agents/`, `app/graph/`, `tests/`, `tests/fixtures/`, `tests/unit/`, `tests/integration/`
4. Add `__init__.py` files to each package directory

## Group 2 — Core Data Contracts

5. Create `app/models/schemas.py`:
   - `DocumentData` Pydantic model (buyer, seller, goods_description, amounts, currency, country_of_origin, port_of_loading, port_of_discharge, vessel_name, date, doc_type, extraction_confidence)
   - `SanctionsResult` Pydantic model (hits, is_clear, severity, confidence, summary)
   - `PolicyResult` Pydantic model (violations, is_clear, confidence, summary)
   - `ConsistencyResult` Pydantic model (discrepancies, is_clear, confidence, summary)
   - `RiskResult` Pydantic model (score, verdict as `Literal["clear","needs_review","rejected"]`, confidence, risk_factors)
   - `ComplianceReport` Pydantic model (verdict, risk_score, recommendations, sar_warranted, reasoning, audit_summary)
   - `ComplianceState` TypedDict (all fields used across the graph: document_paths, policy_path, document_data, sanctions_result, policy_result, consistency_result, risk_result, compliance_report, human_decision, errors, thread_id)
6. Write unit test `tests/unit/models/test_schemas.py`: TypedDict construction, Pydantic field constraints, Literal enforcement on verdict

## Group 3 — PDF Tool

7. Create `app/tools/pdf_reader.py`:
   - `extract_text(path: str) -> str` using `pypdf`
   - Returns empty string (not an exception) for unreadable/missing files
   - Caller is responsible for checking len < 100 chars
8. Write unit test `tests/unit/tools/test_pdf_reader.py`:
   - Valid PDF returns non-empty string
   - Non-PDF / missing file returns empty string without raising
   - File with < 100 chars extracted returns that short string (caller logic tested separately)

## Group 4 — Mock Watchlist Tool

9. Create `app/tools/watchlist.py`:
   - Hard-coded mock data: sanctioned companies, vessels, high-risk countries, high-risk ports, prohibited goods categories
   - `check_entity(name: str) -> dict` — returns `{hit: bool, severity: str, match: str | None}`
   - `check_vessel(name: str) -> dict`
   - `check_country(name: str) -> dict`
   - `check_port(name: str) -> dict`
   - `check_goods(description: str) -> dict`
   - Case-insensitive matching; no fuzzy matching in Phase 1
10. Write unit test `tests/unit/tools/test_watchlist.py`:
    - Known sanctioned entity returns `hit=True` with correct severity
    - Unknown entity returns `hit=False`
    - Case-insensitive match works
    - High-risk country lookup returns expected result

## Group 5 — Logging Utility

11. Create `app/utils/logging.py`:
    - `structlog`-based JSON logger, configured via `LOG_LEVEL` env var
    - `get_logger(name: str) -> BoundLogger`
    - `mask_sensitive_field(value: str) -> str` — returns SHA256 hex digest prefixed `[ENTITY:<hash[:8]>]`
    - Logger must never be called with raw PII — masking is the caller's responsibility; this module provides the helper
12. Write unit test `tests/unit/` (or add to conftest) verifying `mask_sensitive_field` returns the same hash for the same input and never returns the original value

## Group 6 — Shared Test Fixtures

13. Create `tests/conftest.py` with shared fixtures: `sample_compliance_state`, `sample_document_data`, placeholder for `mock_llm` (to be used in Phase 2+)
14. Create `tests/fixtures/` text files: `sample_invoice.txt`, `sample_bol.txt`, `sample_flagged_invoice.txt`, `sample_policy.txt`
