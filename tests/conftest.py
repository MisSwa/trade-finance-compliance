import os
import pytest

# Disable LangSmith tracing in all test runs
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
# Provide a test-safe model name so env["COMPLIANCE_MODEL"] never raises in tests
os.environ.setdefault("COMPLIANCE_MODEL", "claude-sonnet-4-5")

from app.models.schemas import ComplianceState, DocumentData


@pytest.fixture
def sample_document_data() -> DocumentData:
    return DocumentData(
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


@pytest.fixture
def sample_compliance_state(sample_document_data) -> ComplianceState:
    return {
        "document_paths": ["tests/fixtures/sample_invoice.txt"],
        "policy_path": None,
        "document_data": sample_document_data,
        "sanctions_result": None,
        "policy_result": None,
        "consistency_result": None,
        "risk_result": None,
        "compliance_report": None,
        "human_decision": None,
        "errors": [],
        "thread_id": "test-thread-001",
    }


@pytest.fixture
def mock_llm(mocker):
    """Placeholder fixture for Phase 2+ LLM mocking."""
    return mocker.MagicMock()
