# Requirements — Phase 2: Single-Agent Pipeline (Document Extractor)

## Scope

Introduce the first LLM call: a single-node LangGraph pipeline that reads PDF trade documents, extracts structured data via Claude, and surfaces results via a CLI. LangSmith tracing is wired but not validated in the merge gate (no API key required).

### In scope

| Deliverable | File | Notes |
|---|---|---|
| Document extractor agent | `app/agents/document_extractor.py` | LangGraph node; uses `with_structured_output(DocumentData)` |
| Minimal single-node graph | `app/graph/workflow.py` | `START → document_extractor → END`; MemorySaver checkpointer |
| CLI entry point | `main.py` | Accepts PDF path(s); prints extracted JSON |
| Unit test — extractor | `tests/unit/agents/test_document_extractor.py` | Mocked LLM; no real API calls |
| Integration test — graph | `tests/integration/test_graph_routing.py` | Mocked LLM; full graph run |

### Out of scope

- Sanctions, policy, or consistency checking (Phase 3)
- Risk scoring or report generation (Phase 3)
- Human-in-the-loop interrupt (Phase 4)
- Streamlit UI (Phase 4)
- Verifying the LangSmith trace in the UI (deferred — no API key required for merge)
- Retry logic on LLM failures

---

## Decisions

### LLM configuration
Use `ChatAnthropic` from `langchain-anthropic`. Model name is read from the `COMPLIANCE_MODEL` env var exactly as specified in tech-stack.md — no fallback default is added. If the env var is unset, LangChain will raise a configuration error at runtime, which is the correct failure mode (misconfiguration should not silently proceed).

### Structured output
Use `llm.with_structured_output(DocumentData)` to force Claude to return a typed `DocumentData` Pydantic object. If the call raises a `ValidationError` or any exception, the node catches it, logs a privacy-safe error (`document_extractor_failed`, no PII), sets `extraction_confidence=0.0`, and appends to `state["errors"]`. The graph does not crash.

### Graph state initialisation
`run_graph()` builds the initial `ComplianceState` with all optional fields set to `None` and `errors` set to `[]`. The `thread_id` is passed in by the caller (generated as a UUID in `main.py`).

### CLI interface
`main.py` uses `argparse`. Positional argument: one or more PDF paths. Optional `--policy` flag. Prints `document_data.model_dump_json(indent=2)` to stdout on success. Exits with code 1 if extraction failed.

### LangSmith tracing
Enabled automatically when `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` are set in the environment. No code changes needed — LangChain picks these up. The merge gate does not require a trace to be present in the UI.

---

## Context

Phase 2 is the first phase that makes real LLM calls. It depends on Phase 1 for:
- `ComplianceState` TypedDict (state contract for the graph)
- `DocumentData` Pydantic model (structured output target)
- `pdf_reader.extract_text()` (PDF ingestion)
- `get_logger()` and `mask_sensitive_field()` (privacy-safe logging)

`workflow.py` in this phase is intentionally minimal — a single node. It will be replaced wholesale in Phase 3 with the full multi-agent graph. The `run_graph()` helper signature must remain stable across phases so `main.py` does not need to change.

The extractor prompt must request all twelve `DocumentData` fields. Where a field cannot be determined from the document text, Claude should return an empty string or `0.0` rather than hallucinating a value — this is a compliance context where false data is worse than a missing field.
