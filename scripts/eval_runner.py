"""
LangSmith evaluation logic for the trade finance compliance system.

- verdict_evaluator: custom evaluator that checks compliance_report.verdict
- build_dataset: creates or retrieves the LangSmith dataset
- run_evaluation: entry point; dry_run=True avoids all API calls
"""

import contextlib
import os
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

from app.models.schemas import (
    ComplianceReport,
    ConsistencyResult,
    DocumentData,
    PolicyResult,
    SanctionsResult,
)
from scripts.eval_dataset import EVAL_CASES


# ---------------------------------------------------------------------------
# LangSmith evaluator
# ---------------------------------------------------------------------------

def verdict_evaluator(run: Any, example: Any) -> dict:
    """Binary evaluator: returns score=1 if run verdict matches expected label."""
    try:
        actual = (run.outputs or {}).get("verdict")
    except Exception:
        actual = None

    expected = (example.outputs or {}).get("verdict")
    return {"key": "verdict_match", "score": 1 if actual == expected else 0}


# ---------------------------------------------------------------------------
# LangSmith dataset management
# ---------------------------------------------------------------------------

def build_dataset(client: Any) -> Any:
    """Create the LangSmith dataset if it does not exist, then return it.

    Uses get-or-create semantics so repeated calls are idempotent.
    """
    dataset_name = "trade-finance-compliance-v1"

    existing = list(client.list_datasets(dataset_name=dataset_name))
    if existing:
        return existing[0]

    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description=(
            "Labelled trade finance compliance cases for verdict accuracy evaluation. "
            "Three cases: one per verdict (clear, rejected, needs_review)."
        ),
    )
    for case in EVAL_CASES:
        client.create_example(
            inputs={
                "document_paths": case["document_paths"],
                "policy_path": case.get("policy_path"),
            },
            outputs={"verdict": case["label"]},
            dataset_id=dataset.id,
            metadata={"case_id": case["case_id"]},
        )

    return dataset


# ---------------------------------------------------------------------------
# Dry-run helpers
# ---------------------------------------------------------------------------

def _make_mock_llm(return_value: Any) -> MagicMock:
    """Wrap a Pydantic object in a mock ChatAnthropic that returns it on invoke."""
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = return_value
    mock_instance = MagicMock()
    mock_instance.with_structured_output.return_value = mock_structured
    return mock_instance


_SAMPLE_DOC = DocumentData(
    buyer="Good Faith Importers Ltd",
    seller="Reliable Exports GmbH",
    goods_description="Industrial machinery parts — non-controlled",
    amounts=[50000.0],
    currency="USD",
    country_of_origin="Germany",
    port_of_loading="Hamburg",
    port_of_discharge="Rotterdam",
    vessel_name="MV Sunrise",
    date="2024-03-01",
    doc_type="invoice",
    extraction_confidence=0.95,
)

_SUFFICIENT_TEXT = (
    "Sufficient document text for extraction — more than one hundred "
    "characters total so the unreadable-PDF guard does not trigger."
)


def _build_mock_responses(label: str) -> dict:
    """Return predetermined Pydantic objects for each agent based on expected label."""
    if label == "clear":
        return {
            "doc_data": _SAMPLE_DOC,
            "sanctions": SanctionsResult(
                hits=[], is_clear=True, severity="none", confidence=0.92,
                summary="No sanctions hits found.",
            ),
            "policy": PolicyResult(
                violations=[], is_clear=True, confidence=0.92,
                summary="No policy violations.",
            ),
            "consistency": ConsistencyResult(
                discrepancies=[], is_clear=True, confidence=0.92,
                summary="Documents are consistent.",
            ),
            "report": ComplianceReport(
                verdict="clear", risk_score=0.0,
                recommendations=["No further action required."],
                sar_warranted=False,
                reasoning="All agents returned clear with high confidence.",
                audit_summary="Transaction cleared by automated compliance review.",
            ),
        }

    if label == "rejected":
        return {
            "doc_data": _SAMPLE_DOC,
            "sanctions": SanctionsResult(
                hits=["seller: Zarkon Trading Corporation (severity: critical)"],
                is_clear=False, severity="critical", confidence=0.97,
                summary="Critical sanctions hit: seller is a sanctioned entity.",
            ),
            "policy": PolicyResult(
                violations=[], is_clear=True, confidence=0.90,
                summary="No policy violations.",
            ),
            "consistency": ConsistencyResult(
                discrepancies=[], is_clear=True, confidence=0.90,
                summary="Documents are consistent.",
            ),
            "report": ComplianceReport(
                verdict="rejected", risk_score=0.97,
                recommendations=["Reject transaction immediately.", "File SAR."],
                sar_warranted=True,
                reasoning="Critical sanctions hit found. Transaction must be rejected.",
                audit_summary="Transaction rejected due to critical sanctions hit on seller.",
            ),
        }

    # needs_review
    return {
        "doc_data": _SAMPLE_DOC,
        "sanctions": SanctionsResult(
            hits=[], is_clear=True, severity="none", confidence=0.90,
            summary="No sanctions hits found.",
        ),
        "policy": PolicyResult(
            violations=[
                "Missing HS code on goods description",
                "Generic buyer name 'Generic Trading Inc' not verifiable",
                "Advance payment in full for transaction exceeding USD 100,000",
            ],
            is_clear=False, confidence=0.88,
            summary="Multiple policy violations found.",
        ),
        "consistency": ConsistencyResult(
            discrepancies=[], is_clear=True, confidence=0.90,
            summary="Documents are consistent.",
        ),
        "report": ComplianceReport(
            verdict="needs_review", risk_score=0.4,
            recommendations=[
                "Request HS code from seller.",
                "Verify buyer identity via EDD.",
                "Review advance payment terms.",
            ],
            sar_warranted=False,
            reasoning="Policy violations found. Human review required before decision.",
            audit_summary="Transaction escalated to human review due to policy violations.",
        ),
    }


def _run_case_dry(case: dict) -> dict:
    """Run one evaluation case with all LLM calls mocked. Returns the final graph state."""
    from langgraph.types import Command

    from app.graph.workflow import graph, run_graph

    responses = _build_mock_responses(case["label"])
    thread_id = f"eval-dry-{case['case_id']}-{uuid.uuid4().hex[:8]}"

    patches = [
        patch(
            "app.agents.document_extractor.ChatAnthropic",
            return_value=_make_mock_llm(responses["doc_data"]),
        ),
        patch(
            "app.agents.sanctions_screener.ChatAnthropic",
            return_value=_make_mock_llm(responses["sanctions"]),
        ),
        patch(
            "app.agents.policy_checker.ChatAnthropic",
            return_value=_make_mock_llm(responses["policy"]),
        ),
        patch(
            "app.agents.consistency_checker.ChatAnthropic",
            return_value=_make_mock_llm(responses["consistency"]),
        ),
        patch(
            "app.agents.report_generator.ChatAnthropic",
            return_value=_make_mock_llm(responses["report"]),
        ),
        patch(
            "app.agents.document_extractor.extract_text",
            return_value=_SUFFICIENT_TEXT,
        ),
    ]

    with contextlib.ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        run_graph(case["document_paths"], case.get("policy_path"), thread_id)

        config = {"configurable": {"thread_id": thread_id}}
        gs = graph.get_state(config)

        if gs.next and "human_review" in gs.next:
            final_state = run_graph(
                document_paths=[],
                policy_path=None,
                thread_id=thread_id,
                resume_command=Command(resume="approved"),
            )
        else:
            final_state = gs.values

    return final_state


def _run_dry_evaluation() -> None:
    """Run all eval cases locally with mocked LLMs. Raises AssertionError on any failure."""
    # COMPLIANCE_MODEL is read by agents before the mocked ChatAnthropic is invoked.
    # The value is irrelevant in dry-run (no real API calls); set a safe fallback.
    os.environ.setdefault("COMPLIANCE_MODEL", "claude-sonnet-4-5")
    print("Running evaluation in dry-run mode (no LangSmith API calls)...")
    failures: list[str] = []

    for case in EVAL_CASES:
        state = _run_case_dry(case)
        report = state.get("compliance_report")
        actual = report.verdict if report else None
        expected = case["label"]

        label = f"Case {case['case_id']} ({expected})"
        if actual == expected:
            print(f"  {label}: PASS")
        else:
            print(f"  {label}: FAIL (got '{actual}')")
            failures.append(case["case_id"])

    total = len(EVAL_CASES)
    passed = total - len(failures)
    print(f"Evaluation complete. Accuracy: {passed}/{total} cases matched.")

    if failures:
        raise AssertionError(f"Failing cases: {', '.join(failures)}")


# ---------------------------------------------------------------------------
# Live evaluation (requires LANGCHAIN_API_KEY)
# ---------------------------------------------------------------------------

def _run_live_evaluation() -> None:
    """Run evaluation against the live LangSmith API and upload results."""
    try:
        from langsmith import Client
        from langsmith.evaluation import evaluate
    except ImportError as exc:
        raise SystemExit("langsmith package not found. Install requirements.txt.") from exc

    if not os.environ.get("LANGCHAIN_API_KEY"):
        raise SystemExit(
            "LANGCHAIN_API_KEY is not set. Add it to your .env file, "
            "or use --dry-run for local evaluation."
        )

    client = Client()
    dataset = build_dataset(client)

    def _target(inputs: dict) -> dict:
        from langgraph.types import Command

        from app.graph.workflow import graph, run_graph

        thread_id = f"eval-live-{uuid.uuid4().hex[:8]}"
        run_graph(inputs["document_paths"], inputs.get("policy_path"), thread_id)

        config = {"configurable": {"thread_id": thread_id}}
        gs = graph.get_state(config)
        if gs.next and "human_review" in gs.next:
            final_state = run_graph(
                document_paths=[],
                policy_path=None,
                thread_id=thread_id,
                resume_command=Command(resume="approved"),
            )
        else:
            final_state = gs.values

        report = final_state.get("compliance_report")
        return {"verdict": report.verdict if report else None}

    evaluate(
        _target,
        data=dataset.name,
        evaluators=[verdict_evaluator],
        experiment_prefix="trade-finance-v1-eval",
    )
    print("Live evaluation complete. Results visible in LangSmith UI.")
    print(f"Dataset: {dataset.name}")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_evaluation(dry_run: bool = False) -> None:
    """Run evaluation. Set dry_run=True for local CI checks (no API calls)."""
    if dry_run:
        _run_dry_evaluation()
    else:
        _run_live_evaluation()
