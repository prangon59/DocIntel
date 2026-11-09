"""Generate real test fixtures for Phase 1 automated tests:
1. digital_invoice.pdf (digital PDF with selectable text)
2. scanned_invoice.png (scanned bitmap image for OCR)
3. multi_sheet_invoices.xlsx (multi-sheet Excel with merged cells)
4. invoices.csv (valid comma-delimited spreadsheet)
5. corrupted.pdf (corrupted binary payload)
"""

from pathlib import Path

import fitz  # PyMuPDF
import openpyxl
from PIL import Image, ImageDraw

FIXTURES_DIR = Path(__file__).parent


def create_digital_pdf(output_path: Path) -> None:
    """Create a digital PDF with PyMuPDF containing selectable text."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    text = """INVOICE #INV-2024-001
Date: 2024-05-15
Supplier: Acme Industrial Supplies Ltd
Customer: Global Logistics Corp
Currency: USD

Line Items:
1. Heavy Duty Widget A    Qty: 10   Unit Price: 25.00   Total: 250.00
2. Precision Gadget B     Qty: 2    Unit Price: 125.00  Total: 250.00

Subtotal: 500.00
Tax: 50.00
Total: 550.00
"""
    # Insert text at position (50, 70)
    page.insert_text(fitz.Point(50, 70), text, fontsize=12)
    doc.save(str(output_path))
    doc.close()


def create_scanned_image(output_path: Path) -> None:
    """Create a bitmap PNG image simulating a scanned invoice."""
    width, height = 800, 600
    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)

    text_lines = [
        "INVOICE #INV-SCAN-900",
        "Date: 2024-06-10",
        "Supplier: Fast Freight Logistics Inc",
        "Customer: Acme Corp",
        "Freight Shipping Service: $300.00",
        "Fuel Surcharge: $40.00",
        "Total: $340.00 USD",
    ]

    y = 50
    for line in text_lines:
        draw.text((50, y), line, fill="black")
        y += 40

    image.save(str(output_path))


def create_scanned_pdf(output_path: Path, image_path: Path) -> None:
    """Create a PDF with embedded image and NO selectable digital text (<30 chars) to test OCR fallback."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    # Insert image into page
    page.insert_image(page.rect, filename=str(image_path))
    doc.save(str(output_path))
    doc.close()


def create_multisheet_xlsx(output_path: Path) -> None:
    """Create a multi-sheet Excel file with merged cells and structured data."""
    wb = openpyxl.Workbook()

    # Sheet 1: Summary with merged header
    ws1 = wb.active
    ws1.title = "Vendor Invoices"
    ws1.merge_cells("A1:E1")
    ws1["A1"] = "Q2 2024 Vendor Invoices Report"

    ws1.append([])  # Empty row
    headers1 = ["Invoice Number", "Supplier", "Date", "Total", "Status"]
    ws1.append(headers1)
    ws1.append(["INV-XLS-001", "Delta Global", "2024-04-10", 1250.00, "Approved"])
    ws1.append(["INV-XLS-002", "Omega Tech", "2024-04-15", 3400.50, "Pending"])

    # Sheet 2: Line items detail
    ws2 = wb.create_sheet(title="Line Item Details")
    headers2 = ["Invoice Number", "Description", "Quantity", "Unit Price", "Line Total"]
    ws2.append(headers2)
    ws2.append(["INV-XLS-001", "Server Blade Gen 10", 2, 500.00, 1000.00])
    ws2.append(["INV-XLS-001", "RAM Module 64GB", 4, 62.50, 250.00])
    ws2.append(["INV-XLS-002", "Cloud License Annual", 1, 3400.50, 3400.50])

    wb.save(str(output_path))
    wb.close()


def create_csv_file(output_path: Path) -> None:
    """Create a valid CSV file with invoice data."""
    content = """Invoice Number,Supplier,Date,Total,Currency
INV-CSV-101,Office Depot Inc,2024-06-01,129.50,USD
INV-CSV-102,Apex Hardware Ltd,2024-06-05,450.00,USD
INV-CSV-103,Metro Courier Services,2024-06-08,75.25,USD
"""
    output_path.write_text(content, encoding="utf-8")


def create_corrupted_file(output_path: Path) -> None:
    """Create a corrupted PDF file with broken header and damaged binary stream."""
    corrupted_bytes = b"%PDF-1.7 Corrupted Content\x00\xff\xfe\xaa\xbb" + (b"\x00\x01\x02\x03" * 50)
    output_path.write_bytes(corrupted_bytes)


def generate_all_fixtures() -> None:
    """Generate all required fixtures into the tests/fixtures directory."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    digital_pdf = FIXTURES_DIR / "digital_invoice.pdf"
    scanned_png = FIXTURES_DIR / "scanned_invoice.png"
    scanned_pdf = FIXTURES_DIR / "scanned_fallback.pdf"
    xlsx_file = FIXTURES_DIR / "multi_sheet_invoices.xlsx"
    csv_file = FIXTURES_DIR / "invoices.csv"
    corrupted_file = FIXTURES_DIR / "corrupted.pdf"

    create_digital_pdf(digital_pdf)
    create_scanned_image(scanned_png)
    create_scanned_pdf(scanned_pdf, scanned_png)
    create_multisheet_xlsx(xlsx_file)
    create_csv_file(csv_file)
    create_corrupted_file(corrupted_file)

    print(f"Generated 6 fixtures in {FIXTURES_DIR}")


if __name__ == "__main__":
    generate_all_fixtures()
