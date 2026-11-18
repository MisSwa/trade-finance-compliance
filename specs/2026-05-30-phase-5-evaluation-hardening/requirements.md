# Phase 5 — LangSmith Evaluation + Hardening: Requirements

## Scope

Implement a measurable quality layer over the Phase 1–4 system:

- A LangSmith evaluation dataset with three labelled cases (one per verdict)
- A custom evaluator that checks `compliance_report.verdict` against the expected label
- A CLI script (`scripts/run_eval.py`) that runs evaluation locally in dry-run mode or against the live LangSmith API
- Hardening of two known failure modes: unreadable PDFs and unhandled agent exceptions
- A complete README covering setup, demo, tracing, and evaluation

No new agents, no new graph nodes, no changes to the `ComplianceState` schema. The public interface of `run_graph()` is unchanged.

---

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Dataset size | 3 cases (one per verdict) | Matches the three possible verdicts; sufficient for a prototype eval; each case is traceable back to an existing test fixture |
| Dataset source | Programmatically built from `tests/fixtures/` | Reuses existing fixtures, keeps dataset and tests in sync, no manual JSON authoring |
| Dataset location | `scripts/eval_dataset.py` (module) | Importable by both the eval runner and unit tests; no static JSON file to keep in sync |
| LangSmith dataset name | `trade-finance-compliance-v1` | Fixed name; `build_dataset()` uses `get_or_create` semantics so re-runs are idempotent |
| Evaluator granularity | Verdict match only (binary) | Verdict is the single most auditable signal; reasoning quality is not programmatically scorable in v1 |
| Error boundary location | Per-agent node (existing pattern) | Consistent with the try/except pattern established in Phase 3; each agent owns its own failure mode; failures stay contained and don't cascade |
| Error boundary behaviour | Log privacy-safe message, set confidence=0.0, append to `state["errors"]`, return partial result | Matches Phase 3 contract; downstream risk scorer treats confidence=0.0 as a trigger for human review routing |
| Unreadable PDF threshold | < 100 characters total across all extracted documents | Established in roadmap; checked by the extractor agent after `extract_text()` calls, before the LLM call |
| Merge gate for eval | `--dry-run` local pass only | Avoids requiring a live `LANGCHAIN_API_KEY` in CI; dry-run uses the same mocked LLM infrastructure as all other tests |
| README scope | Replace existing README.md entirely | Current README is a placeholder; Phase 5 is the appropriate time for a complete handoff document |

---

## Context

### What Phase 5 adds to the existing system

Phases 1–4 delivered a working prototype. Phase 5 makes it verifiable and maintainable:

- **Evaluation** answers: "Does the system produce the right verdicts on known cases?" It is not a benchmark — it is a regression check.
- **Hardening** answers two specific failure modes called out in the roadmap:
  1. Unreadable PDFs (scanned documents where `pypdf` returns near-empty text)
  2. Unhandled agent exceptions (network errors, malformed LLM responses, unexpected schema mismatches)

Both failure modes already have a defined recovery path in the architecture: route to `human_review`. Phase 5 enforces this path in code and tests that it works.

### What Phase 5 does NOT change

- `ComplianceState` schema — no new fields
- `run_graph()` signature — unchanged
- Agent logic — only exception handling is added where missing; no behavioural changes
- LangSmith tracing — already active from Phase 2; Phase 5 adds an evaluation dataset on top

### Evaluation dry-run mechanics

In dry-run mode, `run_evaluation(dry_run=True)`:

1. Builds cases from `eval_dataset.py` without uploading to LangSmith
2. For each case, calls `run_graph()` with a mocked `ChatAnthropic` (same mock as unit tests)
3. Asserts `state["compliance_report"].verdict == case["label"]`
4. Raises `AssertionError` listing failing case IDs if any assertion fails
5. No network calls to Anthropic or LangSmith are made

In live mode (`--dry-run` omitted):

1. Builds or retrieves the dataset in LangSmith via `langsmith.Client`
2. Calls `evaluate()` from the LangSmith SDK with the `verdict_evaluator`
3. Results appear in the LangSmith UI under the `trade-finance-compliance-v1` dataset
4. Script exits 0 if all three cases score 1; exits 1 if any case fails

### Configuration

No new environment variables are introduced. Existing variables used in Phase 5:

| Variable | Used by | Purpose |
|---|---|---|
| `LANGCHAIN_API_KEY` | `run_eval.py` (live mode only) | Authenticate with LangSmith |
| `LANGCHAIN_TRACING_V2` | Existing; set to `false` in tests | Suppress tracing during dry-run and unit tests |
| `ANTHROPIC_API_KEY` | Existing; mocked in tests | Real key needed only for live mode |
| `COMPLIANCE_MODEL` | Existing | Model used by agents in live mode |
| `CONFIDENCE_THRESHOLD` | Existing | Controls routing in risk scorer |
