import pytest
from pydantic import ValidationError
from app.models.schemas import (
    ComplianceState,
    DocumentData,
    SanctionsResult,
    PolicyResult,
    ConsistencyResult,
    RiskResult,
    ComplianceReport,
)


@pytest.mark.unit
def test_compliance_state_constructs_as_plain_dict():
    state: ComplianceState = {
        "document_paths": ["invoice.pdf"],
        "policy_path": None,
        "document_data": None,
        "sanctions_result": None,
        "policy_result": None,
        "consistency_result": None,
        "risk_result": None,
        "compliance_report": None,
        "human_decision": None,
        "errors": [],
        "thread_id": "test-thread-1",
    }
    assert state["document_paths"] == ["invoice.pdf"]
    assert state["errors"] == []
    assert state["thread_id"] == "test-thread-1"


@pytest.mark.unit
def test_risk_result_rejects_invalid_verdict():
    with pytest.raises(ValidationError):
        RiskResult(score=0.5, verdict="approved", confidence=0.9, risk_factors=[])


@pytest.mark.unit
@pytest.mark.parametrize("verdict", ["clear", "needs_review", "rejected"])
def test_risk_result_accepts_valid_verdicts(verdict):
    r = RiskResult(score=0.5, verdict=verdict, confidence=0.9, risk_factors=[])
    assert r.verdict == verdict


@pytest.mark.unit
def test_risk_result_rejects_score_out_of_range():
    with pytest.raises(ValidationError):
        RiskResult(score=1.5, verdict="clear", confidence=0.9, risk_factors=[])


@pytest.mark.unit
def test_document_data_requires_all_fields():
    with pytest.raises(ValidationError):
        DocumentData(extraction_confidence=0.9)


@pytest.mark.unit
def test_document_data_constructs_correctly():
    d = DocumentData(
        buyer="Acme Corp",
        seller="Beta Exports",
        goods_description="Electronic components",
        amounts=[10000.0],
        currency="USD",
        country_of_origin="Germany",
        port_of_loading="Hamburg",
        port_of_discharge="Rotterdam",
        vessel_name="MV Example",
        date="2024-01-15",
        doc_type="invoice",
        extraction_confidence=0.95,
    )
    assert d.doc_type == "invoice"
    assert d.extraction_confidence == 0.95
    assert d.amounts == [10000.0]


@pytest.mark.unit
def test_compliance_report_requires_recommendations():
    with pytest.raises(ValidationError):
        ComplianceReport(verdict="clear", risk_score=0.1, sar_warranted=False, reasoning="ok")


@pytest.mark.unit
def test_sanctions_result_constructs():
    r = SanctionsResult(hits=[], is_clear=True, severity="none", confidence=0.95, summary="No hits")
    assert r.is_clear is True
    assert r.hits == []
