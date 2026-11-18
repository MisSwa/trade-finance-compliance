# Plan — Phase 2: Single-Agent Pipeline (Document Extractor)

Each task group is independently completable. Within a group, tasks are ordered by dependency.

---

## Group 1 — Document Extractor Agent

1. Create `app/agents/document_extractor.py`:
   - Import `ChatAnthropic` from `langchain_anthropic`; read model name from `COMPLIANCE_MODEL` env var
   - Import `DocumentData` from `app.models.schemas`
   - Define `extract_documents(state: ComplianceState) -> dict` as the LangGraph node function
   - Inside the node: read `state["document_paths"]` and optional `state["policy_path"]`; call `pdf_reader.extract_text()` for each path; concatenate extracted text
   - Call `llm.with_structured_output(DocumentData).invoke(prompt)` with extracted text
   - On success: return `{"document_data": result, "errors": state["errors"]}`
   - On `ValidationError` or any exception: log a privacy-safe error event; return `{"document_data": None, "errors": state["errors"] + ["document_extractor_failed"], "document_data": DocumentData(..., extraction_confidence=0.0)}`
   - Prompt must instruct Claude to extract all `DocumentData` fields from the provided document text

2. Write unit test `tests/unit/agents/test_document_extractor.py`:
   - Mock `ChatAnthropic` so no real API call is made
   - Test: valid document text → returns correctly populated `DocumentData` in state
   - Test: LLM raises exception → returns `extraction_confidence=0.0` and appends error to `state["errors"]`
   - Test: node returns only the keys it updates (does not overwrite unrelated state fields)

## Group 2 — Minimal Workflow

3. Create `app/graph/workflow.py`:
   - Build a `StateGraph(ComplianceState)` with a single node: `"document_extractor"` → `extract_documents`
   - Add `START → document_extractor → END` edges
   - Attach `MemorySaver` checkpointer
   - Expose a `compile()` call; store the compiled graph as module-level `graph`
   - Export a `run_graph(document_paths: list[str], policy_path: str | None, thread_id: str) -> ComplianceState` helper that builds initial state and invokes the graph

4. Write integration test `tests/integration/test_graph_routing.py`:
   - Mock the extractor node's LLM call
   - Test: graph runs start-to-end and final state contains a populated `document_data`
   - Test: graph runs start-to-end with LLM failure and final state contains `"document_extractor_failed"` in `errors`

## Group 3 — CLI Entry Point

5. Create `main.py` at the project root:
   - Accept a PDF path as a CLI argument (use `argparse` or `sys.argv`)
   - Optional `--policy` flag for a policy PDF path
   - Call `workflow.run_graph()` with the provided paths and a generated `thread_id`
   - Print the resulting `DocumentData` as formatted JSON to stdout
   - On failure (no `document_data` or `extraction_confidence == 0.0`): print an error message and exit with code 1
   - Load `.env` via `python-dotenv` at startup
