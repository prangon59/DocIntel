"""Synthetic Labeled Dataset Generator for Document Intelligence System Evaluation.

Generates 36 diverse synthetic documents across:
- Clean digital PDFs with varied layouts and multi-page documents
- Scanned PDFs and PNG/JPG images with synthetic noise, rotation jitter, and blur
- Multi-sheet Excel spreadsheets (XLSX) with title banners and CSV files
- Deliberate math errors (subtotal + tax != total, line item sum mismatch)
- Duplicate invoice pairs (exact and fuzzy matching)
- Corrupted and malformed files (0-byte, truncated binary, spoofed archive)
Along with paired ground-truth JSON files for each document.
"""

import csv
import json
import random
from decimal import Decimal
from pathlib import Path
from typing import Any

import pymupdf
from openpyxl import Workbook
from PIL import Image, ImageDraw, ImageFilter

DATASET_DIR = Path(__file__).parent / "dataset"
FILES_DIR = DATASET_DIR / "files"
GT_DIR = DATASET_DIR / "ground_truth"


def _add_noise_and_rotation(img: Image.Image, angle_range: float = 2.0) -> Image.Image:
    """Add slight synthetic rotation, speckles, and blur to simulate scanning."""
    angle = random.uniform(-angle_range, angle_range)
    # Rotate with white background expansion
    rotated = img.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True, fillcolor="white")

    # Add random speckles
    draw = ImageDraw.Draw(rotated)
    w, h = rotated.size
    for _ in range(int(w * h * 0.0005)):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        draw.point((x, y), fill="gray")

    # Slight blur
    blurred = rotated.filter(ImageFilter.GaussianBlur(radius=0.4))
    return blurred


def _create_digital_pdf(
    file_path: Path,
    invoice_number: str,
    supplier: str,
    customer: str,
    inv_date: str,
    currency: str,
    line_items: list[dict[str, Any]],
    subtotal: Decimal,
    tax: Decimal,
    total: Decimal,
    multi_page: bool = False,
) -> None:
    """Create clean digital PDF invoice using PyMuPDF."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4 size

    # Header Banner
    page.draw_rect(pymupdf.Rect(40, 40, 555, 90), color=(0.15, 0.35, 0.7), fill=(0.92, 0.95, 1.0))
    page.insert_text(
        (55, 75), f"INVOICE #{invoice_number}", fontsize=20, fontname="helv", color=(0.1, 0.2, 0.5)
    )

    # Metadata
    page.insert_text((55, 115), f"Supplier: {supplier}", fontsize=11, fontname="helv")
    page.insert_text((55, 130), f"Customer: {customer}", fontsize=11, fontname="helv")
    page.insert_text((380, 115), f"Invoice Date: {inv_date}", fontsize=11, fontname="helv")
    page.insert_text((380, 130), f"Currency: {currency}", fontsize=11, fontname="helv")

    # Table Header
    y = 165
    page.draw_rect(pymupdf.Rect(40, y, 555, y + 20), color=(0.7, 0.7, 0.7), fill=(0.85, 0.85, 0.85))
    page.insert_text((50, y + 14), "Description", fontsize=10, fontname="helv")
    page.insert_text((310, y + 14), "Qty", fontsize=10, fontname="helv")
    page.insert_text((380, y + 14), "Unit Price", fontsize=10, fontname="helv")
    page.insert_text((470, y + 14), "Line Total", fontsize=10, fontname="helv")

    y += 25
    for item in line_items:
        page.insert_text((50, y + 12), str(item["description"]), fontsize=9, fontname="helv")
        page.insert_text((310, y + 12), str(item["quantity"]), fontsize=9, fontname="helv")
        page.insert_text(
            (380, y + 12), f"{Decimal(str(item['unit_price'])):.2f}", fontsize=9, fontname="helv"
        )
        page.insert_text(
            (470, y + 12), f"{Decimal(str(item['line_total'])):.2f}", fontsize=9, fontname="helv"
        )
        page.draw_line(
            pymupdf.Point(40, y + 18), pymupdf.Point(555, y + 18), color=(0.85, 0.85, 0.85)
        )
        y += 22

    # Totals block
    y += 15
    page.draw_rect(
        pymupdf.Rect(350, y, 555, y + 65), color=(0.8, 0.8, 0.8), fill=(0.98, 0.98, 0.98)
    )
    page.insert_text(
        (365, y + 18), f"Subtotal: {currency} {subtotal:.2f}", fontsize=10, fontname="helv"
    )
    page.insert_text(
        (365, y + 36), f"Tax (10%): {currency} {tax:.2f}", fontsize=10, fontname="helv"
    )
    page.insert_text(
        (365, y + 54),
        f"Grand Total: {currency} {total:.2f}",
        fontsize=11,
        fontname="helv",
        color=(0.1, 0.1, 0.4),
    )

    if multi_page:
        # Add Page 2: Terms & payment details
        p2 = doc.new_page(width=595, height=842)
        p2.insert_text(
            (50, 60), f"Payment Terms for Invoice #{invoice_number}", fontsize=14, fontname="helv"
        )
        p2.insert_text((50, 90), f"Beneficiary: {supplier}", fontsize=10, fontname="helv")
        p2.insert_text(
            (50, 110),
            "Wire Transfer: Bank of America, Routing #026009593",
            fontsize=10,
            fontname="helv",
        )
        p2.insert_text((50, 130), "Due Date: Net 30 Days", fontsize=10, fontname="helv")

    doc.save(str(file_path))
    doc.close()


def _create_scanned_image_or_pdf(
    file_path: Path,
    invoice_number: str,
    supplier: str,
    customer: str,
    inv_date: str,
    currency: str,
    line_items: list[dict[str, Any]],
    subtotal: Decimal,
    tax: Decimal,
    total: Decimal,
    as_pdf: bool = False,
) -> None:
    """Create scanned invoice image with noise and rotation, saving as PNG, JPG, or PDF."""
    w, h = 800, 1100
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)

    # Text rendering using PIL default font
    draw.text((60, 50), f"INVOICE #{invoice_number}", fill="black")
    draw.text((60, 100), f"Supplier: {supplier}", fill="black")
    draw.text((60, 130), f"Customer: {customer}", fill="black")
    draw.text((500, 100), f"Date: {inv_date}", fill="black")
    draw.text((500, 130), f"Currency: {currency}", fill="black")

    draw.line([(50, 170), (750, 170)], fill="black", width=2)
    draw.text((60, 180), "Item Description", fill="black")
    draw.text((450, 180), "Qty", fill="black")
    draw.text((550, 180), "Price", fill="black")
    draw.text((660, 180), "Total", fill="black")
    draw.line([(50, 205), (750, 205)], fill="gray", width=1)

    y = 220
    for item in line_items:
        draw.text((60, y), str(item["description"]), fill="black")
        draw.text((450, y), str(item["quantity"]), fill="black")
        draw.text((550, y), f"{Decimal(str(item['unit_price'])):.2f}", fill="black")
        draw.text((660, y), f"{Decimal(str(item['line_total'])):.2f}", fill="black")
        y += 35

    draw.line([(450, y + 10), (750, y + 10)], fill="black", width=1)
    y += 25
    draw.text((460, y), f"Subtotal: {subtotal:.2f}", fill="black")
    draw.text((460, y + 30), f"Tax: {tax:.2f}", fill="black")
    draw.text((460, y + 60), f"Total: {total:.2f}", fill="black")

    # Add scanner artifacts
    noisy_img = _add_noise_and_rotation(img)

    if as_pdf:
        noisy_img.save(str(file_path), "PDF", resolution=150.0)
    elif file_path.suffix.lower() == ".jpg" or file_path.suffix.lower() == ".jpeg":
        noisy_img.save(str(file_path), "JPEG", quality=85)
    else:
        noisy_img.save(str(file_path), "PNG")


def _create_xlsx_file(
    file_path: Path,
    invoices: list[dict[str, Any]],
) -> None:
    """Create multi-sheet XLSX invoice ledger."""
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Current Invoices"

    # Banner title
    ws1.merge_cells("A1:G1")
    ws1["A1"] = "MONTHLY ACCOUNTS PAYABLE LEDGER"

    headers = ["Invoice No", "Date", "Vendor Name", "Subtotal", "Tax", "Grand Total", "Currency"]
    ws1.append(headers)

    for inv in invoices:
        ws1.append(
            [
                inv["invoice_number"],
                inv["invoice_date"],
                inv["supplier_name"],
                float(inv["subtotal"]),
                float(inv["tax"]),
                float(inv["total"]),
                inv["currency"],
            ]
        )

    # Sheet 2: Historical
    ws2 = wb.create_sheet(title="Archived Records")
    ws2.append(["Reference", "Vendor", "Total Amount"])
    ws2.append(["OLD-REF-001", "Legacy Corp", 120.00])

    wb.save(str(file_path))


def _create_csv_file(
    file_path: Path,
    invoices: list[dict[str, Any]],
) -> None:
    """Create CSV invoice file."""
    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["invoice_num", "inv_date", "supplier", "subtotal", "tax_amount", "total_amt", "curr"]
        )
        for inv in invoices:
            writer.writerow(
                [
                    inv["invoice_number"],
                    inv["invoice_date"],
                    inv["supplier_name"],
                    str(inv["subtotal"]),
                    str(inv["tax"]),
                    str(inv["total"]),
                    inv["currency"],
                ]
            )


def _save_ground_truth(filename: str, gt_data: dict[str, Any]) -> None:
    """Save ground truth JSON pairing."""
    gt_path = GT_DIR / f"{filename}.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(gt_data, f, indent=2, default=str)


def generate_evaluation_dataset() -> list[str]:
    """Generate the full evaluation dataset of 36 documents and paired ground truth."""
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    GT_DIR.mkdir(parents=True, exist_ok=True)

    generated_files: list[str] = []

    # -------------------------------------------------------------------------
    # 1. Digital PDFs (10 documents)
    # -------------------------------------------------------------------------
    for i in range(1, 11):
        fname = f"digital_inv_{i:02d}.pdf"
        fpath = FILES_DIR / fname
        inv_num = f"INV-2025-DIG-{i:03d}"
        supplier = f"TechCorp Enterprise {i} Inc."
        customer = f"Client Solutions {i} LLC"
        inv_date = f"2025-01-{10 + i:02d}"
        currency = "USD"
        q1, p1 = Decimal("2.00"), Decimal("150.00")
        q2, p2 = Decimal("4.00"), Decimal("50.00")
        items = [
            {
                "description": f"Cloud Hosting Tier {i}",
                "quantity": q1,
                "unit_price": p1,
                "line_total": q1 * p1,
            },
            {
                "description": f"Database Support Unit {i}",
                "quantity": q2,
                "unit_price": p2,
                "line_total": q2 * p2,
            },
        ]
        subtotal = sum(item["line_total"] for item in items)
        tax = round(subtotal * Decimal("0.10"), 2)
        total = subtotal + tax

        _create_digital_pdf(
            fpath,
            inv_num,
            supplier,
            customer,
            inv_date,
            currency,
            items,
            subtotal,
            tax,
            total,
            multi_page=(i % 3 == 0),
        )

        gt = {
            "filename": fname,
            "file_type": "pdf",
            "is_valid": True,
            "expected_status": "COMPLETED",
            "expected_fields": {
                "invoice_number": inv_num,
                "supplier_name": supplier,
                "customer_name": customer,
                "invoice_date": inv_date,
                "subtotal": str(subtotal),
                "tax": str(tax),
                "total": str(total),
                "currency": currency,
            },
            "expected_line_items": [
                {
                    "description": it["description"],
                    "quantity": str(it["quantity"]),
                    "unit_price": str(it["unit_price"]),
                    "line_total": str(it["line_total"]),
                }
                for it in items
            ],
            "expected_validation_issues": [],
            "expected_needs_review": False,
        }
        _save_ground_truth(fname, gt)
        generated_files.append(fname)

    # -------------------------------------------------------------------------
    # 2. Scanned PDFs & Images (8 documents: 4 PDF, 2 PNG, 2 JPG)
    # -------------------------------------------------------------------------
    scanned_specs = [
        ("scanned_inv_01.pdf", "pdf", True),
        ("scanned_inv_02.pdf", "pdf", True),
        ("scanned_inv_03.pdf", "pdf", True),
        ("scanned_inv_04.pdf", "pdf", True),
        ("scanned_inv_05.png", "png", False),
        ("scanned_inv_06.png", "png", False),
        ("scanned_inv_07.jpg", "jpg", False),
        ("scanned_inv_08.jpg", "jpg", False),
    ]

    for idx, (fname, ftype, as_pdf) in enumerate(scanned_specs, start=1):
        fpath = FILES_DIR / fname
        inv_num = f"INV-2025-SCN-{idx:03d}"
        supplier = f"Heavy Logistics Supplies {idx}"
        customer = f"Industrial Logistics {idx}"
        inv_date = f"2025-02-{idx + 5:02d}"
        currency = "USD"
        q1, p1 = Decimal("10.00"), Decimal("25.00")
        items = [
            {
                "description": f"Hydraulic Parts Set {idx}",
                "quantity": q1,
                "unit_price": p1,
                "line_total": q1 * p1,
            }
        ]
        subtotal = Decimal("250.00")
        tax = Decimal("25.00")
        total = Decimal("275.00")

        _create_scanned_image_or_pdf(
            fpath,
            inv_num,
            supplier,
            customer,
            inv_date,
            currency,
            items,
            subtotal,
            tax,
            total,
            as_pdf=as_pdf,
        )

        gt = {
            "filename": fname,
            "file_type": ftype,
            "is_valid": True,
            "expected_status": "COMPLETED",
            "expected_fields": {
                "invoice_number": inv_num,
                "supplier_name": supplier,
                "customer_name": customer,
                "invoice_date": inv_date,
                "subtotal": str(subtotal),
                "tax": str(tax),
                "total": str(total),
                "currency": currency,
            },
            "expected_line_items": [
                {
                    "description": it["description"],
                    "quantity": str(it["quantity"]),
                    "unit_price": str(it["unit_price"]),
                    "line_total": str(it["line_total"]),
                }
                for it in items
            ],
            "expected_validation_issues": [],
            "expected_needs_review": False,
        }
        _save_ground_truth(fname, gt)
        generated_files.append(fname)

    # -------------------------------------------------------------------------
    # 3. Spreadsheets (8 documents: 4 XLSX, 4 CSV)
    # -------------------------------------------------------------------------
    for i in range(1, 5):
        fname_xlsx = f"spreadsheet_inv_{i:02d}.xlsx"
        fpath_xlsx = FILES_DIR / fname_xlsx
        inv_data = {
            "invoice_number": f"INV-2025-XLS-{i:03d}",
            "invoice_date": f"2025-03-{i + 10:02d}",
            "supplier_name": f"Spreadsheet Vendor {i} LLC",
            "subtotal": Decimal("400.00"),
            "tax": Decimal("40.00"),
            "total": Decimal("440.00"),
            "currency": "USD",
        }
        _create_xlsx_file(fpath_xlsx, [inv_data])

        gt_xlsx = {
            "filename": fname_xlsx,
            "file_type": "xlsx",
            "is_valid": True,
            "expected_status": "COMPLETED",
            "expected_fields": {
                "invoice_number": inv_data["invoice_number"],
                "supplier_name": inv_data["supplier_name"],
                "customer_name": None,
                "invoice_date": inv_data["invoice_date"],
                "subtotal": str(inv_data["subtotal"]),
                "tax": str(inv_data["tax"]),
                "total": str(inv_data["total"]),
                "currency": inv_data["currency"],
            },
            "expected_line_items": [],
            "expected_validation_issues": [],
            "expected_needs_review": False,
        }
        _save_ground_truth(fname_xlsx, gt_xlsx)
        generated_files.append(fname_xlsx)

    for i in range(5, 9):
        fname_csv = f"spreadsheet_inv_{i:02d}.csv"
        fpath_csv = FILES_DIR / fname_csv
        inv_data = {
            "invoice_number": f"INV-2025-CSV-{i:03d}",
            "invoice_date": f"2025-03-{i + 10:02d}",
            "supplier_name": f"CSV Data Supplier {i} Corp",
            "subtotal": Decimal("300.00"),
            "tax": Decimal("30.00"),
            "total": Decimal("330.00"),
            "currency": "USD",
        }
        _create_csv_file(fpath_csv, [inv_data])

        gt_csv = {
            "filename": fname_csv,
            "file_type": "csv",
            "is_valid": True,
            "expected_status": "COMPLETED",
            "expected_fields": {
                "invoice_number": inv_data["invoice_number"],
                "supplier_name": inv_data["supplier_name"],
                "customer_name": None,
                "invoice_date": inv_data["invoice_date"],
                "subtotal": str(inv_data["subtotal"]),
                "tax": str(inv_data["tax"]),
                "total": str(inv_data["total"]),
                "currency": inv_data["currency"],
            },
            "expected_line_items": [],
            "expected_validation_issues": [],
            "expected_needs_review": False,
        }
        _save_ground_truth(fname_csv, gt_csv)
        generated_files.append(fname_csv)

    # -------------------------------------------------------------------------
    # 4. Deliberate Math Mismatches (4 documents: 2 PDF, 1 XLSX, 1 CSV)
    # -------------------------------------------------------------------------
    math_specs = [
        (
            "math_err_01.pdf",
            "pdf",
            Decimal("500.00"),
            Decimal("50.00"),
            Decimal("650.00"),
        ),  # 500+50 != 650
        ("math_err_02.pdf", "pdf", Decimal("1000.00"), Decimal("100.00"), Decimal("1250.00")),
        ("math_err_03.xlsx", "xlsx", Decimal("300.00"), Decimal("30.00"), Decimal("400.00")),
        ("math_err_04.csv", "csv", Decimal("200.00"), Decimal("20.00"), Decimal("300.00")),
    ]

    for fname, ftype, sub, tx, tot in math_specs:
        fpath = FILES_DIR / fname
        inv_num = f"INV-MATH-ERR-{fname[:11]}"
        supplier = "Faulty Accounting LLC"
        customer = "Review Dept"
        inv_date = "2025-04-01"
        currency = "USD"
        items = [
            {
                "description": "Audit Consulting",
                "quantity": Decimal("1.00"),
                "unit_price": sub,
                "line_total": sub,
            }
        ]

        if ftype == "pdf":
            _create_digital_pdf(
                fpath, inv_num, supplier, customer, inv_date, currency, items, sub, tx, tot
            )
        elif ftype == "xlsx":
            _create_xlsx_file(
                fpath,
                [
                    {
                        "invoice_number": inv_num,
                        "invoice_date": inv_date,
                        "supplier_name": supplier,
                        "subtotal": sub,
                        "tax": tx,
                        "total": tot,
                        "currency": currency,
                    }
                ],
            )
        else:
            _create_csv_file(
                fpath,
                [
                    {
                        "invoice_number": inv_num,
                        "invoice_date": inv_date,
                        "supplier_name": supplier,
                        "subtotal": sub,
                        "tax": tx,
                        "total": tot,
                        "currency": currency,
                    }
                ],
            )

        gt = {
            "filename": fname,
            "file_type": ftype,
            "is_valid": False,
            "expected_status": "COMPLETED",
            "expected_fields": {
                "invoice_number": inv_num,
                "supplier_name": supplier,
                "customer_name": customer if ftype == "pdf" else None,
                "invoice_date": inv_date,
                "subtotal": str(sub),
                "tax": str(tx),
                "total": str(tot),
                "currency": currency,
            },
            "expected_line_items": items if ftype == "pdf" else [],
            "expected_validation_issues": ["MATH_MISMATCH_TOTAL"],
            "expected_needs_review": True,
        }
        _save_ground_truth(fname, gt)
        generated_files.append(fname)

    # -------------------------------------------------------------------------
    # 5. Duplicate Invoices (3 documents: 1 exact pair + 1 fuzzy)
    # -------------------------------------------------------------------------
    dup_specs = [
        (
            "duplicate_inv_01a.pdf",
            "INV-DUP-PRIMARY",
            "Acme Dual Services LLC",
            Decimal("100.00"),
            Decimal("10.00"),
            Decimal("110.00"),
            False,
            [],
        ),
        (
            "duplicate_inv_01b.pdf",
            "INV-DUP-PRIMARY",
            "Acme Dual Services LLC",
            Decimal("100.00"),
            Decimal("10.00"),
            Decimal("110.00"),
            True,
            ["DUPLICATE_INVOICE_EXACT"],
        ),
        (
            "duplicate_inv_02_fuzzy.pdf",
            "INV-DUP-FUZZY",
            "Acme Dual Services Inc",
            Decimal("100.00"),
            Decimal("10.00"),
            Decimal("110.00"),
            True,
            ["DUPLICATE_INVOICE_FUZZY"],
        ),
    ]

    for fname, inv_num, supp, sub, tx, tot, needs_rev, exp_issues in dup_specs:
        fpath = FILES_DIR / fname
        customer = "Client Target"
        inv_date = "2025-05-15"
        currency = "USD"
        items = [
            {
                "description": "Service Item",
                "quantity": Decimal("1.00"),
                "unit_price": sub,
                "line_total": sub,
            }
        ]

        _create_digital_pdf(fpath, inv_num, supp, customer, inv_date, currency, items, sub, tx, tot)

        gt = {
            "filename": fname,
            "file_type": "pdf",
            "is_valid": not needs_rev,
            "expected_status": "COMPLETED",
            "expected_fields": {
                "invoice_number": inv_num,
                "supplier_name": supp,
                "customer_name": customer,
                "invoice_date": inv_date,
                "subtotal": str(sub),
                "tax": str(tx),
                "total": str(tot),
                "currency": currency,
            },
            "expected_line_items": items,
            "expected_validation_issues": exp_issues,
            "expected_needs_review": needs_rev,
        }
        _save_ground_truth(fname, gt)
        generated_files.append(fname)

    # -------------------------------------------------------------------------
    # 6. Corrupted / Malformed Documents (3 documents)
    # -------------------------------------------------------------------------
    # 6.1 Zero-byte PDF
    f1 = FILES_DIR / "corrupted_01_empty.pdf"
    f1.write_bytes(b"")
    gt1 = {
        "filename": "corrupted_01_empty.pdf",
        "file_type": "unknown",
        "is_valid": False,
        "expected_status": "FAILED",
        "expected_fields": {},
        "expected_line_items": [],
        "expected_validation_issues": [],
        "expected_needs_review": False,
    }
    _save_ground_truth("corrupted_01_empty.pdf", gt1)
    generated_files.append("corrupted_01_empty.pdf")

    # 6.2 Truncated binary header
    f2 = FILES_DIR / "corrupted_02_truncated.pdf"
    f2.write_bytes(b"%PDF-1.4\n%Broken truncated binary payload with no trailer\n")
    gt2 = {
        "filename": "corrupted_02_truncated.pdf",
        "file_type": "pdf",
        "is_valid": False,
        "expected_status": "FAILED",
        "expected_fields": {},
        "expected_line_items": [],
        "expected_validation_issues": [],
        "expected_needs_review": False,
    }
    _save_ground_truth("corrupted_02_truncated.pdf", gt2)
    generated_files.append("corrupted_02_truncated.pdf")

    # 6.3 Spoofed corrupted archive (garbage bytes with xlsx extension)
    f3 = FILES_DIR / "corrupted_03_fake.xlsx"
    f3.write_bytes(b"PK\x03\x04\x00\x00Garbage corrupted zip content not a real spreadsheet")
    gt3 = {
        "filename": "corrupted_03_fake.xlsx",
        "file_type": "xlsx",
        "is_valid": False,
        "expected_status": "FAILED",
        "expected_fields": {},
        "expected_line_items": [],
        "expected_validation_issues": [],
        "expected_needs_review": False,
    }
    _save_ground_truth("corrupted_03_fake.xlsx", gt3)
    generated_files.append("corrupted_03_fake.xlsx")

    return generated_files


def main() -> None:
    print(f"Generating synthetic evaluation dataset in {DATASET_DIR}...")
    files = generate_evaluation_dataset()
    print(
        f"Successfully generated {len(files)} synthetic evaluation documents with paired ground truth."
    )


if __name__ == "__main__":
    main()
