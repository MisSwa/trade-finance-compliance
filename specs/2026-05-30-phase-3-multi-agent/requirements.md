# Requirements — Phase 3: Full Multi-Agent System

## Scope

Extend the single-node pipeline into a full multi-agent system: three parallel screening agents, a rule-based risk scorer, a report generator, and a complete LangGraph workflow with conditional routing to human review.

### In scope

| Deliverable | File | Notes |
|---|---|---|
| Sanctions screener | `app/agents/sanctions_screener.py` | Watchlist lookup + Claude summary; returns `SanctionsResult` |
| Policy checker | `app/agents/policy_checker.py` | Claude evaluates document data against policy text; returns `PolicyResult` |
| Consistency checker | `app/agents/consistency_checker.py` | Claude cross-checks field values for discrepancies; returns `ConsistencyResult` |
| Risk scorer | `app/agents/risk_scorer.py` | Rule-based aggregation; no LLM call; returns `RiskResult` |
| Report generator | `app/agents/report_generator.py` | Claude produces final `ComplianceReport` |
| Full workflow | `app/graph/workflow.py` (replaced) | Parallel fan-out, risk routing, human_review stub, `run_graph()` unchanged |
| Unit tests | `tests/unit/agents/` + `tests/unit/workflow/` | All agents + routing function tested with mocked LLM |

### Out of scope

- Human-in-the-loop `interrupt()` (Phase 4) — `human_review` node is a passthrough stub in this phase
- Streamlit UI (Phase 4)
- LangSmith evaluation datasets (Phase 5)
- Retry logic on LLM failures
- Fuzzy matching on watchlist lookups (still exact match from Phase 1)

---

## Decisions

### Parallel fan-out
The three screening agents (sanctions, policy, consistency) run in parallel using LangGraph's native parallel node execution. All three write to separate, non-overlapping fields of `ComplianceState` (`sanctions_result`, `policy_result`, `consistency_result`), so there are no write conflicts.

### Risk scorer — no LLM
The risk scorer is intentionally rule-based, not LLM-driven. Routing logic must be deterministic and auditable: the rules are explicit code, not emergent model behaviour. This is consistent with the project's "accuracy over speed" and "auditability" principles.

### Routing logic
`CONFIDENCE_THRESHOLD` is read from the environment at runtime (default `0.7` if not set). The routing function is a pure Python function extracted from the graph builder so it can be unit-tested independently of the graph.

### Human review stub
The `human_review` node in Phase 3 is a passthrough that routes directly to `report_generator`. It exists in the graph so the routing edges are correct and testable. It will be replaced with the `interrupt()` implementation in Phase 4 without changing the graph topology.

### `run_graph()` signature stability
`run_graph(document_paths, policy_path, thread_id)` is unchanged from Phase 2. `main.py` requires no modification.

### Agent failure handling
Each agent follows the same contract as `document_extractor`: catch all exceptions, log a privacy-safe event, return a minimal result with `confidence=0.0` and `is_clear=False`, append an error string to `state["errors"]`. The risk scorer treats `confidence=0.0` as low confidence and routes to human review.

---

## Context

Phase 3 is the core compliance logic of the system. The routing rules implement the FATF-aligned compliance policy:

- A confirmed sanctions hit (`is_clear=False` from `sanctions_screener`) is the highest-risk outcome and produces `"rejected"`.
- Policy violations or document inconsistencies produce `"needs_review"` for human adjudication.
- Low-confidence extractions (`confidence < 0.7`) escalate to human review even if no specific issue was found — consistent with the "graceful degradation" principle in `mission.md`.

The `human_review` stub preserves the graph structure so integration tests can verify routing without requiring a full Phase 4 implementation. The test fixtures from Phase 1 (`sample_invoice.txt`, `sample_flagged_invoice.txt`) serve as the basis for the unit test scenarios.
