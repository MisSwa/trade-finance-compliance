from pypdf import PdfReader


def extract_text(path: str) -> str:
    """Extract text from a PDF file. Returns empty string on any failure."""
    try:
        reader = PdfReader(path)
        return "".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""
