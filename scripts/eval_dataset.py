"""
Labelled evaluation cases for Phase 5 LangSmith evaluation.

Each case maps document fixture paths to an expected verdict so the
verdict_evaluator can score model outputs against a known ground truth.
"""

EVAL_CASES: list[dict] = [
    {
        "case_id": "case-a-clear",
        "document_paths": ["tests/fixtures/sample_invoice.txt"],
        "policy_path": None,
        "label": "clear",
    },
    {
        "case_id": "case-b-rejected",
        "document_paths": ["tests/fixtures/sample_flagged_invoice.txt"],
        "policy_path": None,
        "label": "rejected",
    },
    {
        "case_id": "case-c-needs-review",
        "document_paths": ["tests/fixtures/sample_inconsistent_invoice.txt"],
        "policy_path": None,
        "label": "needs_review",
    },
]
