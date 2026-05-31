import pytest
from unittest.mock import MagicMock

from scripts.eval_runner import run_evaluation, verdict_evaluator


# ---------------------------------------------------------------------------
# verdict_evaluator unit tests
# ---------------------------------------------------------------------------

def _make_run(verdict):
    run = MagicMock()
    run.outputs = {"verdict": verdict}
    return run


def _make_example(verdict):
    example = MagicMock()
    example.outputs = {"verdict": verdict}
    return example


@pytest.mark.unit
def test_verdict_evaluator_match():
    result = verdict_evaluator(_make_run("clear"), _make_example("clear"))
    assert result["key"] == "verdict_match"
    assert result["score"] == 1


@pytest.mark.unit
def test_verdict_evaluator_mismatch():
    result = verdict_evaluator(_make_run("clear"), _make_example("rejected"))
    assert result["key"] == "verdict_match"
    assert result["score"] == 0


@pytest.mark.unit
def test_verdict_evaluator_none_output():
    """Evaluator handles missing verdict gracefully — returns score 0."""
    run = MagicMock()
    run.outputs = {}
    result = verdict_evaluator(run, _make_example("clear"))
    assert result["score"] == 0


@pytest.mark.unit
def test_dry_run_all_cases_pass():
    """All three fixture cases produce the correct verdict with mocked LLM calls."""
    # run_evaluation(dry_run=True) internally uses unittest.mock.patch —
    # no real LangSmith or Anthropic API calls are made.
    run_evaluation(dry_run=True)
