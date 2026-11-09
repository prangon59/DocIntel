"""Unit tests for multi-sheet XLSX and CSV parsing with merged cell handling."""

from pathlib import Path

import pytest

from app.services.spreadsheet.parser import (
    SpreadsheetProcessingError,
    parse_csv,
    parse_spreadsheet,
    parse_xlsx,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_multisheet_xlsx():
    xlsx_path = str(FIXTURES_DIR / "multi_sheet_invoices.xlsx")
    sheets = parse_xlsx(xlsx_path)

    assert len(sheets) == 2
    sheet1, sheet2 = sheets[0], sheets[1]

    # Sheet 1 assertions
    assert sheet1.sheet_name == "Vendor Invoices"
    assert sheet1.row_count >= 2
    assert "Invoice Number" in sheet1.headers
    assert any("INV-XLS-001" in str(r.values()) for r in sheet1.rows)

    # Sheet 2 assertions
    assert sheet2.sheet_name == "Line Item Details"
    assert "Description" in sheet2.headers
    assert any("Server Blade" in str(r.values()) for r in sheet2.rows)


def test_parse_csv_file():
    csv_path = str(FIXTURES_DIR / "invoices.csv")
    sheets = parse_csv(csv_path)

    assert len(sheets) == 1
    sheet = sheets[0]
    assert sheet.row_count == 3
    assert "Invoice Number" in sheet.headers
    assert any("INV-CSV-101" in str(r.values()) for r in sheet.rows)
    assert any("Office Depot" in str(r.values()) for r in sheet.rows)


def test_parse_unsupported_spreadsheet():
    with pytest.raises(SpreadsheetProcessingError):
        parse_spreadsheet("fake_file.doc", file_type="doc")
