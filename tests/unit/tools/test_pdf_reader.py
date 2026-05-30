import pytest
from unittest.mock import MagicMock
from app.tools.pdf_reader import extract_text


@pytest.mark.unit
def test_missing_file_returns_empty_string():
    result = extract_text("/nonexistent/path/to/missing.pdf")
    assert result == ""


@pytest.mark.unit
def test_non_pdf_file_returns_empty_string(tmp_path):
    txt_file = tmp_path / "document.txt"
    txt_file.write_text("This is not a PDF")
    result = extract_text(str(txt_file))
    assert result == ""


@pytest.mark.unit
def test_valid_pdf_returns_extracted_text(mocker):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Commercial Invoice — Buyer: Acme Corp — Amount: $10,000 USD"
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]
    mocker.patch("app.tools.pdf_reader.PdfReader", return_value=mock_reader)

    result = extract_text("fake.pdf")

    assert "Invoice" in result
    assert len(result) > 0


@pytest.mark.unit
def test_multipage_pdf_concatenates_all_pages(mocker):
    pages = [MagicMock(), MagicMock()]
    pages[0].extract_text.return_value = "Page one content. "
    pages[1].extract_text.return_value = "Page two content."
    mock_reader = MagicMock()
    mock_reader.pages = pages
    mocker.patch("app.tools.pdf_reader.PdfReader", return_value=mock_reader)

    result = extract_text("multipage.pdf")

    assert "Page one" in result
    assert "Page two" in result


@pytest.mark.unit
def test_page_returning_none_handled_gracefully(mocker):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = None
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]
    mocker.patch("app.tools.pdf_reader.PdfReader", return_value=mock_reader)

    result = extract_text("scanned.pdf")

    assert result == ""
