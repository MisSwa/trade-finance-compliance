from typing import Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from typing import Literal


class DocumentData(BaseModel):
    buyer: str
    seller: str
    goods_description: str
    amounts: list[float]
    currency: str
    country_of_origin: str
    port_of_loading: str
    port_of_discharge: str
    vessel_name: str
    date: str
    doc_type: str
    extraction_confidence: float = Field(ge=0.0, le=1.0)


class SanctionsResult(BaseModel):
    hits: list[str]
    is_clear: bool
    severity: str
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str


class PolicyResult(BaseModel):
    violations: list[str]
    is_clear: bool
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str


class ConsistencyResult(BaseModel):
    discrepancies: list[str]
    is_clear: bool
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str


class RiskResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    verdict: Literal["clear", "needs_review", "rejected"]
    confidence: float = Field(ge=0.0, le=1.0)
    risk_factors: list[str]


class ComplianceReport(BaseModel):
    verdict: str
    risk_score: float = Field(ge=0.0, le=1.0)
    recommendations: list[str]
    sar_warranted: bool
    reasoning: str
    audit_summary: str


class ComplianceState(TypedDict):
    document_paths: list[str]
    policy_path: Optional[str]
    document_data: Optional[DocumentData]
    sanctions_result: Optional[SanctionsResult]
    policy_result: Optional[PolicyResult]
    consistency_result: Optional[ConsistencyResult]
    risk_result: Optional[RiskResult]
    compliance_report: Optional[ComplianceReport]
    human_decision: Optional[str]
    errors: list[str]
    thread_id: str
