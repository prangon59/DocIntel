"""Unit tests for magic-byte file sniffing and format validation."""

from pathlib import Path

from app.services.ingest.detector import detect_file_type

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_detect_digital_pdf():
    pdf_bytes = (FIXTURES_DIR / "digital_invoice.pdf").read_bytes()
    res = detect_file_type(pdf_bytes, filename="digital_invoice.pdf")
    assert res.is_supported is True
    assert res.file_type == "pdf"
    assert res.mime_type == "application/pdf"


def test_detect_png_image():
    png_bytes = (FIXTURES_DIR / "scanned_invoice.png").read_bytes()
    res = detect_file_type(png_bytes, filename="scanned_invoice.png")
    assert res.is_supported is True
    assert res.file_type == "png"
    assert res.mime_type == "image/png"


def test_detect_multisheet_xlsx():
    xlsx_bytes = (FIXTURES_DIR / "multi_sheet_invoices.xlsx").read_bytes()
    res = detect_file_type(xlsx_bytes, filename="multi_sheet_invoices.xlsx")
    assert res.is_supported is True
    assert res.file_type == "xlsx"
    assert "spreadsheetml" in res.mime_type


def test_detect_csv_file():
    csv_bytes = (FIXTURES_DIR / "invoices.csv").read_bytes()
    res = detect_file_type(csv_bytes, filename="invoices.csv")
    assert res.is_supported is True
    assert res.file_type == "csv"
    assert res.mime_type == "text/csv"


def test_detect_empty_file():
    res = detect_file_type(b"", filename="empty.pdf")
    assert res.is_supported is False
    assert res.file_type == "empty"
    assert "empty" in (res.error_message or "").lower()


def test_detect_spoofed_extension():
    """A plain text file renamed to fake.pdf must NOT be detected as PDF."""
    fake_pdf = b"This is just plain text, not a real PDF document at all."
    res = detect_file_type(fake_pdf, filename="fake.pdf")
    assert res.file_type != "pdf"


def test_detect_corrupted_archive():
    """A ZIP signature without Excel OpenXML parts is rejected as XLSX."""
    corrupted_zip = b"PK\x03\x04\x00\x00\x00\x00NotAnExcelFile"
    res = detect_file_type(corrupted_zip, filename="fake.xlsx")
    assert res.file_type != "xlsx"
    assert res.is_supported is False
