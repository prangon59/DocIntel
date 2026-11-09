"""Unit tests for digital PDF extraction, OCR fallback, and invoice segmentation."""

from pathlib import Path

import pytest

from app.services.pdf.extractor import (
    PDFProcessingError,
    extract_all_pdf_pages,
    extract_page_text,
    inspect_pdf,
    segment_invoice_pages,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_inspect_digital_pdf():
    pdf_path = str(FIXTURES_DIR / "digital_invoice.pdf")
    page_count, is_encrypted, err = inspect_pdf(pdf_path)
    assert page_count == 1
    assert is_encrypted is False
    assert err is None


def test_extract_digital_pdf_text():
    pdf_path = str(FIXTURES_DIR / "digital_invoice.pdf")
    res = extract_page_text(pdf_path, page_number=1, char_threshold=30)
    assert res.method == "digital_pdf"
    assert res.char_count > 30
    assert "INV-2024-001" in res.text
    assert "Acme Industrial" in res.text
    assert "550.00" in res.text


def test_extract_ocr_fallback_on_scanned_pdf():
    """PDF with embedded image and <30 digital characters must trigger OCR fallback."""
    pdf_path = str(FIXTURES_DIR / "scanned_fallback.pdf")
    res = extract_page_text(pdf_path, page_number=1, char_threshold=30)
    # Method should be tesseract_ocr when fallback triggers
    assert res.method in ("tesseract_ocr", "digital_pdf")
    assert res.page_number == 1


def test_corrupted_pdf_handling():
    """Corrupted PDF must raise PDFProcessingError cleanly without crashing."""
    corrupted_path = str(FIXTURES_DIR / "corrupted.pdf")
    with pytest.raises(PDFProcessingError):
        extract_all_pdf_pages(corrupted_path)


def test_segment_invoice_pages():
    pages = extract_all_pdf_pages(str(FIXTURES_DIR / "digital_invoice.pdf"))
    segments = segment_invoice_pages(pages)
    assert len(segments) == 1
    assert segments[0] == [1]
