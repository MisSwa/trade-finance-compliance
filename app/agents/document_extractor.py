import os

from langchain_anthropic import ChatAnthropic

from app.models.schemas import ComplianceState, DocumentData
from app.tools.pdf_reader import extract_text
from app.utils.logging import get_logger

logger = get_logger(__name__)

_PROMPT = """You are a trade finance document analyst. Extract structured data from the trade document text below.

Return values exactly as they appear in the document. If a field cannot be determined, return an empty string for text fields, an empty list for amounts, or 0.0 for extraction_confidence. Do not infer or hallucinate values — in compliance contexts a missing field is safer than a wrong one.

Fields to extract:
- buyer: buying party name
- seller: selling party name
- goods_description: description of goods being traded
- amounts: all monetary amounts as a list of floats
- currency: currency code (e.g. USD, EUR, GBP)
- country_of_origin: country where goods originate
- port_of_loading: port where goods are loaded
- port_of_discharge: port where goods are discharged
- vessel_name: name of the vessel
- date: primary document date (ISO format preferred)
- doc_type: one of invoice, bill_of_lading, packing_list, or unknown
- extraction_confidence: your confidence in the overall extraction, 0.0–1.0

Document text:
{text}
"""


def extract_documents(state: ComplianceState) -> dict:
    texts = [
        extract_text(path)
        for path in state["document_paths"]
        if extract_text(path)
    ]
    combined = "\n\n---\n\n".join(texts) if texts else ""

    if len(combined) < 100:
        logger.warning("document_extractor_unreadable_pdf", total_chars=len(combined))
        return {
            "document_data": DocumentData(
                buyer="",
                seller="",
                goods_description="",
                amounts=[],
                currency="",
                country_of_origin="",
                port_of_loading="",
                port_of_discharge="",
                vessel_name="",
                date="",
                doc_type="unknown",
                extraction_confidence=0.0,
            ),
            "errors": state.get("errors", []) + ["document_extractor_unreadable_pdf"],
        }

    model = os.environ["COMPLIANCE_MODEL"]
    llm = ChatAnthropic(model=model)
    structured_llm = llm.with_structured_output(DocumentData)

    try:
        result: DocumentData = structured_llm.invoke(_PROMPT.format(text=combined))
        logger.info(
            "document_extracted",
            doc_type=result.doc_type,
            extraction_confidence=result.extraction_confidence,
        )
        return {"document_data": result}
    except Exception as exc:
        logger.error("document_extractor_failed", error_type=type(exc).__name__)
        return {
            "document_data": DocumentData(
                buyer="",
                seller="",
                goods_description="",
                amounts=[],
                currency="",
                country_of_origin="",
                port_of_loading="",
                port_of_discharge="",
                vessel_name="",
                date="",
                doc_type="unknown",
                extraction_confidence=0.0,
            ),
            "errors": state.get("errors", []) + ["document_extractor_failed"],
        }
