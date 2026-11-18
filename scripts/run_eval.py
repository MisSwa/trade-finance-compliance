"""
CLI entry point for Phase 5 evaluation.

Usage:
    # Local dry-run (no API calls — required for merge gate):
    LANGCHAIN_TRACING_V2=false python scripts/run_eval.py --dry-run

    # Live LangSmith evaluation (requires LANGCHAIN_API_KEY):
    python scripts/run_eval.py
"""

import argparse
import os
import sys

# Ensure the repo root is on sys.path so that `app.*` and `scripts.*` imports
# work whether this file is run as `python scripts/run_eval.py` or as a module.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from dotenv import load_dotenv

load_dotenv()

from scripts.eval_runner import run_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run trade finance compliance evaluation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help=(
            "Run evaluation locally with mocked LLM calls. "
            "No LangSmith or Anthropic API calls are made. "
            "Required for CI merge gate."
        ),
    )
    args = parser.parse_args()

    try:
        run_evaluation(dry_run=args.dry_run)
    except AssertionError as exc:
        print(f"\nEvaluation failed: {exc}", file=sys.stderr)
        sys.exit(1)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"\nUnexpected error: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
