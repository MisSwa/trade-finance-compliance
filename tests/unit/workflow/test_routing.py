import os
import pytest
from app.models.schemas import RiskResult
from app.graph.workflow import route_after_risk_scorer

_BASE_STATE = {
    "document_paths": [],
    "policy_path": None,
    "document_data": None,
    "sanctions_result": None,
    "policy_result": None,
    "consistency_result": None,
    "risk_result": None,
    "compliance_report": None,
    "human_decision": None,
    "errors": [],
    "thread_id": "test-thread",
}


@pytest.mark.unit
def test_clear_verdict_high_confidence_routes_to_report_generator():
    state = {**_BASE_STATE, "risk_result": RiskResult(score=0.05, verdict="clear", confidence=0.9, risk_factors=[])}

    assert route_after_risk_scorer(state) == "report_generator"


@pytest.mark.unit
def test_needs_review_routes_to_human_review():
    state = {**_BASE_STATE, "risk_result": RiskResult(score=0.5, verdict="needs_review", confidence=0.88, risk_factors=["Policy violation"])}

    assert route_after_risk_scorer(state) == "human_review"


@pytest.mark.unit
def test_rejected_routes_to_human_review():
    state = {**_BASE_STATE, "risk_result": RiskResult(score=0.95, verdict="rejected", confidence=0.95, risk_factors=["Critical sanctions hit"])}

    assert route_after_risk_scorer(state) == "human_review"


@pytest.mark.unit
def test_clear_verdict_low_confidence_routes_to_human_review():
    state = {**_BASE_STATE, "risk_result": RiskResult(score=0.1, verdict="clear", confidence=0.5, risk_factors=[])}

    assert route_after_risk_scorer(state) == "human_review"


@pytest.mark.unit
def test_clear_verdict_exactly_at_threshold_routes_to_report_generator():
    os.environ["CONFIDENCE_THRESHOLD"] = "0.7"
    state = {**_BASE_STATE, "risk_result": RiskResult(score=0.05, verdict="clear", confidence=0.7, risk_factors=[])}

    assert route_after_risk_scorer(state) == "report_generator"


@pytest.mark.unit
def test_missing_risk_result_routes_to_human_review():
    state = {**_BASE_STATE, "risk_result": None}

    assert route_after_risk_scorer(state) == "human_review"
