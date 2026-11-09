"""Unit and regression tests for evaluation dataset generator and benchmark runner."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.schemas.extraction import InvoiceExtractionSchema


def test_evaluation_dataset_files_and_ground_truth_pairing() -> None:
    """Verify that all generated dataset files have corresponding ground truth pairs."""
    eval_dir = Path(__file__).resolve().parent.parent.parent / "eval"
    files_dir = eval_dir / "dataset" / "files"
    gt_dir = eval_dir / "dataset" / "ground_truth"

    assert files_dir.exists(), f"Dataset files directory not found at {files_dir}"
    assert gt_dir.exists(), f"Ground truth directory not found at {gt_dir}"

    files = list(files_dir.iterdir())
    gt_files = list(gt_dir.glob("*.json"))

    assert len(files) >= 30, f"Expected at least 30 synthetic documents, found {len(files)}"
    assert len(gt_files) == len(files), (
        f"Mismatch between files ({len(files)}) and ground-truth ({len(gt_files)})"
    )

    # Verify every file has a matching ground truth JSON
    for f in files:
        expected_gt = gt_dir / f"{f.name}.json"
        assert expected_gt.exists(), f"Missing ground truth file for {f.name}"

        with open(expected_gt, encoding="utf-8") as gt_f:
            gt_data = json.load(gt_f)

        assert "filename" in gt_data
        assert "file_type" in gt_data
        assert "is_valid" in gt_data
        assert "expected_status" in gt_data
        assert "expected_fields" in gt_data
        assert "expected_line_items" in gt_data
        assert "expected_validation_issues" in gt_data
        assert "expected_needs_review" in gt_data


def test_evaluation_dataset_diversity() -> None:
    """Verify that the evaluation dataset contains diverse file types and edge cases."""
    eval_dir = Path(__file__).resolve().parent.parent.parent / "eval"
    files_dir = eval_dir / "dataset" / "files"

    filenames = [f.name for f in files_dir.iterdir()]

    pdf_count = sum(1 for name in filenames if name.endswith(".pdf"))
    spreadsheet_count = sum(1 for name in filenames if name.endswith((".xlsx", ".csv")))
    image_count = sum(1 for name in filenames if name.endswith((".png", ".jpg")))
    corrupted_count = sum(1 for name in filenames if "corrupted" in name)
    math_err_count = sum(1 for name in filenames if "math_err" in name)
    duplicate_count = sum(1 for name in filenames if "duplicate" in name)

    assert pdf_count >= 10, f"Expected >= 10 PDFs, got {pdf_count}"
    assert spreadsheet_count >= 6, f"Expected >= 6 spreadsheets, got {spreadsheet_count}"
    assert image_count >= 4, f"Expected >= 4 images, got {image_count}"
    assert corrupted_count >= 3, f"Expected >= 3 corrupted files, got {corrupted_count}"
    assert math_err_count >= 2, f"Expected >= 2 math error files, got {math_err_count}"
    assert duplicate_count >= 2, f"Expected >= 2 duplicate files, got {duplicate_count}"


@pytest.mark.asyncio
async def test_offline_eval_llm_client_parsing() -> None:
    """Test deterministic OfflineEvalLLMClient regex parsing on structured invoice text."""
    import sys

    eval_dir = Path(__file__).resolve().parent.parent.parent / "eval"
    sys.path.insert(0, str(eval_dir))
    from run_eval import OfflineEvalLLMClient

    sample_invoice_text = """
    INVOICE #INV-2025-TEST-99
    Supplier: Acme Logistics Corp.
    Customer: Global Retail Ltd.
    Invoice Date: 2025-05-15
    Currency: USD

    Description Qty Unit Price Line Total
    Express Freight 2.00 120.00 240.00
    Pallet Storage 5.00 20.00 100.00

    Subtotal: USD 340.00
    Tax (10%): USD 34.00
    Grand Total: USD 374.00
    """

    client = OfflineEvalLLMClient()
    extracted: InvoiceExtractionSchema = await client.extract_invoice(sample_invoice_text)

    assert extracted.invoice_number is not None
    assert extracted.invoice_number.value == "INV-2025-TEST-99"

    assert extracted.supplier_name is not None
    assert extracted.supplier_name.value == "Acme Logistics Corp."

    assert extracted.customer_name is not None
    assert extracted.customer_name.value == "Global Retail Ltd."

    assert extracted.invoice_date is not None
    assert extracted.invoice_date.value == "2025-05-15"

    assert extracted.currency is not None
    assert extracted.currency.value == "USD"

    assert extracted.subtotal is not None
    assert extracted.subtotal.value == Decimal("340.00")

    assert extracted.tax is not None
    assert extracted.tax.value == Decimal("34.00")

    assert extracted.total is not None
    assert extracted.total.value == Decimal("374.00")

    assert len(extracted.line_items) == 2
    assert extracted.line_items[0].description.value == "Express Freight"
    assert extracted.line_items[0].quantity.value == Decimal("2.00")
    assert extracted.line_items[0].unit_price.value == Decimal("120.00")
    assert extracted.line_items[0].line_total.value == Decimal("240.00")


def test_markdown_report_formatting() -> None:
    """Test that markdown report generation compiles without error and includes required sections."""
    import sys

    eval_dir = Path(__file__).resolve().parent.parent.parent / "eval"
    sys.path.insert(0, str(eval_dir))
    from run_eval import generate_markdown_report

    mock_summary_data = {
        "execution_mode": "Test Mock Pipeline",
        "total_documents": 36,
        "succeeded_documents": 33,
        "failed_documents": 3,
        "document_success_rate": 91.67,
        "document_failure_rate": 8.33,
        "latency_ms": {
            "avg": 105.0,
            "p50": 65.0,
            "p95": 380.0,
            "min": 20.0,
            "max": 450.0,
        },
        "category_latency": {
            "digital_pdf": {"count": 10, "avg": 65.0, "p95": 95.0},
            "scanned_noisy": {"count": 8, "avg": 250.0, "p95": 420.0},
            "spreadsheet": {"count": 8, "avg": 55.0, "p95": 70.0},
            "math_error": {"count": 4, "avg": 60.0, "p95": 80.0},
            "duplicate": {"count": 3, "avg": 75.0, "p95": 90.0},
            "corrupted": {"count": 3, "avg": 22.0, "p95": 28.0},
        },
        "field_metrics": {
            "invoice_number": {
                "support": 33,
                "tp": 30,
                "fp": 0,
                "fn": 3,
                "precision": 100.0,
                "recall": 90.9,
                "f1": 95.2,
            },
        },
        "line_item_metrics": {
            "expected": 33,
            "extracted": 30,
            "matches": 30,
            "precision": 100.0,
            "recall": 90.9,
            "f1": 95.2,
        },
        "validation_metrics": {
            "expected_issues": 6,
            "flagged_issues": 6,
            "precision": 100.0,
            "recall": 100.0,
            "f1": 100.0,
            "needs_review_accuracy": 95.0,
        },
        "failure_cases": [],
    }

    report = generate_markdown_report(mock_summary_data)
    assert "# AI Document Intelligence System - Evaluation Benchmark Report" in report
    assert "Synthetic Dataset" in report or "synthetic dataset" in report
    assert "Executive Summary" in report
    assert "Processing Latency" in report
    assert "Field-Level Extraction Accuracy" in report
    assert "Validation Engine" in report
    assert "Known Limitations" in report
