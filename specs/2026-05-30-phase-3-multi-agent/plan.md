# Plan — Phase 3: Full Multi-Agent System

Each task group is independently completable. Within a group, tasks are ordered by dependency.

---

## Group 1 — Sanctions Screener Agent

1. Create `app/agents/sanctions_screener.py`:
   - LangGraph node `screen_sanctions(state: ComplianceState) -> dict`
   - Reads `state["document_data"]`; calls `watchlist.check_entity()`, `check_vessel()`, `check_country()`, `check_port()`, `check_goods()` against all relevant fields
   - Uses Claude via `with_structured_output(SanctionsResult)` to interpret hits and produce a natural-language summary
   - On exception: return `SanctionsResult` with `confidence=0.0`, `is_clear=False`, append `"sanctions_screener_failed"` to errors
   - Returns `{"sanctions_result": result}`

2. Write `tests/unit/agents/test_sanctions_screener.py`:
   - Test: document with known sanctioned entity → `is_clear=False`, hit in `hits` list
   - Test: clean document → `is_clear=True`, empty `hits`
   - Test: LLM exception → `confidence=0.0`, error appended
   - Test: node only returns keys it updates

## Group 2 — Policy Checker Agent

3. Create `app/agents/policy_checker.py`:
   - LangGraph node `check_policy(state: ComplianceState) -> dict`
   - Reads `state["document_data"]` and optionally `state["policy_path"]` (reads policy PDF text via `pdf_reader`)
   - Uses Claude via `with_structured_output(PolicyResult)` to identify violations of bank policy rules
   - On exception: return `PolicyResult` with `confidence=0.0`, `is_clear=False`, append `"policy_checker_failed"` to errors
   - Returns `{"policy_result": result}`

4. Write `tests/unit/agents/test_policy_checker.py`:
   - Test: document with advance payment to high-risk jurisdiction → violation found
   - Test: clean document with no policy path → `is_clear=True`
   - Test: LLM exception → `confidence=0.0`, error appended
   - Test: node only returns keys it updates

## Group 3 — Consistency Checker Agent

5. Create `app/agents/consistency_checker.py`:
   - LangGraph node `check_consistency(state: ComplianceState) -> dict`
   - Reads `state["document_data"]`; uses Claude via `with_structured_output(ConsistencyResult)` to cross-check field values (amounts, buyer/seller names, country of origin) for internal inconsistencies
   - On exception: return `ConsistencyResult` with `confidence=0.0`, `is_clear=False`, append `"consistency_checker_failed"` to errors
   - Returns `{"consistency_result": result}`

6. Write `tests/unit/agents/test_consistency_checker.py`:
   - Test: consistent document data → `is_clear=True`, empty `discrepancies`
   - Test: document with amount discrepancy → discrepancy in list
   - Test: LLM exception → `confidence=0.0`, error appended
   - Test: node only returns keys it updates

## Group 4 — Risk Scorer Agent

7. Create `app/agents/risk_scorer.py`:
   - LangGraph node `score_risk(state: ComplianceState) -> dict`
   - Reads `sanctions_result`, `policy_result`, `consistency_result` from state
   - Aggregates findings into a numeric score (0–1) and verdict using rule-based logic (no LLM call needed):
     - Any `is_clear=False` with `severity == "critical"` → `"rejected"`
     - Any `is_clear=False` → `"needs_review"`
     - All `is_clear=True` → `"clear"`
   - `score` = weighted average of `(1 - confidence)` across the three agents; `overall_confidence` = minimum confidence across agents
   - On exception: return `RiskResult` with `score=1.0`, `verdict="needs_review"`, `confidence=0.0`, append `"risk_scorer_failed"`
   - Returns `{"risk_result": result}`

8. Write `tests/unit/agents/test_risk_scorer.py`:
   - Test: all agents clear + high confidence → verdict `"clear"`, score near 0
   - Test: any agent `is_clear=False` → verdict `"needs_review"`
   - Test: critical sanctions hit → verdict `"rejected"`
   - Test: all clear but low confidence → verdict `"clear"` with low `overall_confidence` (routing handled in workflow)
   - Test: node only returns keys it updates

## Group 5 — Report Generator Agent

9. Create `app/agents/report_generator.py`:
   - LangGraph node `generate_report(state: ComplianceState) -> dict`
   - Reads full state (all agent results + `human_decision` if present); uses Claude via `with_structured_output(ComplianceReport)` to produce the final report
   - Prompt must include verdict, risk score, all agent summaries, and human decision if available
   - On exception: append `"report_generator_failed"`, return minimal `ComplianceReport` with verdict from `risk_result`
   - Returns `{"compliance_report": result}`

10. Write `tests/unit/agents/test_report_generator.py`:
    - Test: full clean state → `ComplianceReport` with verdict `"clear"`
    - Test: state with human decision `"approve"` → report includes human decision
    - Test: LLM exception → error appended, minimal report returned
    - Test: node only returns keys it updates

## Group 6 — Full Workflow

11. Replace `app/graph/workflow.py` with the full multi-agent graph:
    - `START → document_extractor`
    - `document_extractor → [sanctions_screener, policy_checker, consistency_checker]` (parallel fan-out)
    - `[sanctions_screener, policy_checker, consistency_checker] → risk_scorer` (fan-in)
    - `risk_scorer → conditional_routing` edge:
      - `verdict == "rejected"` → `human_review` node
      - `verdict == "needs_review"` → `human_review` node
      - `overall_confidence < CONFIDENCE_THRESHOLD` → `human_review` node
      - `verdict == "clear"` AND `confidence >= threshold` → `report_generator`
    - `human_review` node (stub for Phase 4): passes through state unchanged; routes to `report_generator`
    - `report_generator → END`
    - `run_graph()` signature unchanged

12. Write `tests/unit/workflow/test_routing.py`:
    - Test: `route_after_risk_scorer()` returns `"report_generator"` when verdict is `"clear"` and confidence ≥ 0.7
    - Test: returns `"human_review"` when verdict is `"needs_review"`
    - Test: returns `"human_review"` when verdict is `"rejected"`
    - Test: returns `"human_review"` when confidence < 0.7 even if verdict is `"clear"`
