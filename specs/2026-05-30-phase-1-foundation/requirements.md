# Requirements — Phase 1: Foundation

## Scope

Implement the project scaffold and core data contracts required by all later phases. No LLM calls. No agents. No graph execution.

### In scope

| Deliverable | File | Notes |
|---|---|---|
| Pinned dependencies | `requirements.txt` | Includes all libraries from tech-stack.md |
| Environment config template | `.env.example` | All keys from tech-stack.md configurable parameters table |
| Pydantic models | `app/models/schemas.py` | `DocumentData`, `SanctionsResult`, `PolicyResult`, `ConsistencyResult`, `RiskResult`, `ComplianceReport` |
| Graph state contract | `app/models/schemas.py` | `ComplianceState(TypedDict)` — single source of truth for all graph state |
| PDF extraction tool | `app/tools/pdf_reader.py` | `pypdf`-based; returns empty string on failure |
| Mock sanctions data | `app/tools/watchlist.py` | Hard-coded mock; case-insensitive exact matching |
| Structured logger | `app/utils/logging.py` | `structlog` JSON; `mask_sensitive_field()` helper |
| Unit tests | `tests/unit/` | For schemas, pdf_reader, watchlist, mask helper |
| Test fixtures | `tests/fixtures/` | Sample text files; `conftest.py` with shared state fixtures |

### Out of scope

- Any LLM call or import of `langchain-anthropic` / `langgraph` in this phase
- Real PDF files committed to the repo (fixtures are `.txt` files with extracted text)
- Live sanctions API integration
- Streamlit UI
- Fuzzy matching on watchlist lookups

---

## Decisions

### Python packaging
Use `pip` + `venv` as specified in tech-stack.md. No `uv` or `poetry`. `requirements.txt` uses `==` pins for all direct dependencies.

### State architecture
`ComplianceState` is a `TypedDict` (not a Pydantic model). All agent outputs are Pydantic models used only at the LLM boundary; results are unpacked into `ComplianceState` fields after each agent call. This is required by LangGraph's `StateGraph`.

### Mock watchlist data
Provide a realistic but clearly fake dataset — fictional company names, vessel names, and countries/ports drawn from FATF typology examples. Must not use real sanctioned entity names to avoid false test assumptions.

### Logging privacy contract
`mask_sensitive_field(value)` produces a deterministic SHA256 hash. It is the **caller's responsibility** to mask before logging. The logging module does not auto-scan log events for PII. This keeps the implementation simple and testable.

### PDF readability threshold
`pdf_reader.py` does not enforce the 100-character threshold — it returns whatever `pypdf` extracts. The threshold check and routing logic live in the extractor agent (Phase 2). This keeps tools focused on a single concern.

---

## Context

Phase 1 is a pre-requisite for every other phase:
- Phase 2 imports `ComplianceState`, `DocumentData`, and `pdf_reader`
- Phase 3 imports all remaining Pydantic models and `watchlist`
- Phase 4 and 5 depend on the full schema being stable

Changes to `ComplianceState` field names or types after Phase 1 will require updates across all agents. The schema should be treated as a contract once Phase 2 begins.

The project is a compliance decision-support tool for trained bank staff. It must never auto-approve or auto-reject transactions. The foundation phase establishes the data contracts that enforce this — `ComplianceState` carries `human_decision` as a first-class field, signalling that human review is part of the designed workflow, not an afterthought.

Regulatory context: FATF Recommendations 6 and 10; Trade-Based Money Laundering (TBML) detection. The mock watchlist should include goods categories consistent with FATF TBML typologies (dual-use goods, precious metals, arms-adjacent categories).
