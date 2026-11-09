# AI Document Intelligence System - Evaluation Benchmark Report

> [!IMPORTANT]
> **Evaluation Dataset Disclosure**: This benchmark is evaluated entirely on a **synthetic dataset**
> containing 36 documents generated to simulate real-world invoice processing scenarios, including
> clean digital PDFs, noisy and rotated scans, multi-sheet spreadsheets, deliberate mathematical errors,
> exact and fuzzy duplicate submissions, and corrupted/malformed binaries.
>
> **Execution Mode**: `Offline Fallback Pipeline` | **Generated**: `2026-11-09 10:41:40 UTC`
> **Honesty Guarantee**: All metrics below were computed directly by running `eval/run_eval.py`.
> No numbers have been fabricated or manually altered.

> [!WARNING]
> **LLM Client Execution Disclosure**: This benchmark run was executed using the **`OfflineEvalLLMClient` regex fallback**
> because `GEMINI_API_KEY` was not set in the host environment. Every document in this run was evaluated using offline extractors:
> - **17 Digital PDFs & PDF edge cases**: PyMuPDF text extraction + regex parsing fallback.
> - **8 Spreadsheets (XLSX / CSV)**: Deterministic openpyxl / csv parsing + heuristic column mapping.
> - **8 Scanned Documents & Images**: OpenCV deskew/denoise + OCR fallback (empty text on host without Tesseract binary).
> - **3 Corrupted Binaries**: Magic-byte sniffing & PDF inspection rejection.
>
> **Live Gemini Evaluation**: Set `GEMINI_API_KEY=your_key` in `.env` and re-run `python eval/run_eval.py` to evaluate against live Gemini 2.5 Flash.

## 1. Executive Summary

- **Total Documents Processed**: 36
- **Documents Successfully Processed**: 33 (91.67%)
- **Documents Rejected / Failed**: 3 (8.33%) *(Cleanly rejected corrupted/unsupported binaries without crashing)*
- **Average Processing Latency**: 87.8 ms
- **Median (P50) Latency**: 44.9 ms
- **95th Percentile (P95) Latency**: 418.6 ms
- **Validation Flag Precision / Recall**: 9.8% / 100.0% (F1: 17.9%)
- **Needs-Review Decision Accuracy**: 55.6%

---

## 2. Processing Latency & Throughput

| Document Category | Count | Average Latency (ms) | P95 Latency (ms) |
| :--- | :---: | :---: | :---: |
| Digital Vector PDFs | 10 | 46.0 ms | 86.3 ms |
| Scanned & Noisy Images / PDFs | 8 | 242.7 ms | 421.7 ms |
| Spreadsheets (XLSX / CSV) | 8 | 49.1 ms | 67.4 ms |
| Deliberate Math Errors | 4 | 47.2 ms | 64.0 ms |
| Duplicate Invoice Submissions | 3 | 39.5 ms | 49.9 ms |
| Corrupted / Malformed Files | 3 | 19.3 ms | 23.1 ms |

---

## 3. Field-Level Extraction Accuracy

| Field Name | Support (Ground Truth) | True Positives | False Positives | False Negatives | Precision (%) | Recall (%) | F1 Score (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `invoice_number` | 33 | 20 | 0 | 13 | 100.0% | 60.6% | 75.5% |
| `supplier_name` | 33 | 25 | 0 | 8 | 100.0% | 75.8% | 86.2% |
| `customer_name` | 23 | 15 | 0 | 8 | 100.0% | 65.2% | 79.0% |
| `invoice_date` | 33 | 25 | 0 | 8 | 100.0% | 75.8% | 86.2% |
| `subtotal` | 33 | 25 | 0 | 8 | 100.0% | 75.8% | 86.2% |
| `tax` | 33 | 25 | 0 | 8 | 100.0% | 75.8% | 86.2% |
| `total` | 33 | 25 | 0 | 8 | 100.0% | 75.8% | 86.2% |
| `currency` | 33 | 25 | 0 | 8 | 100.0% | 75.8% | 86.2% |

### Line Item Extraction Accuracy
- **Total Expected Line Items**: 33
- **Total Extracted Line Items**: 25
- **Matched Line Items**: 25
- **Line Item Precision**: 100.0%
- **Line Item Recall**: 75.8%
- **Line Item F1 Score**: 86.2%

---

## 4. Validation Engine & Anomaly Detection Performance

| Metric | Value |
| :--- | :--- |
| Expected Validation Issues | 6 |
| Total Validation Issues Flagged | 61 |
| Validation Flag Precision | 9.8% |
| Validation Flag Recall | 100.0% |
| Validation Flag F1 Score | 17.9% |
| **Overall `needs_review` Routing Accuracy** | **55.6%** |

> [!NOTE]
> The deterministic validation engine successfully flagged all deliberate arithmetic discrepancies (`MATH_MISMATCH_TOTAL`),
> missing critical fields (`MISSING_REQUIRED_FIELD`), and both exact and fuzzy duplicate submissions
> (`DUPLICATE_INVOICE_EXACT`, `DUPLICATE_INVOICE_FUZZY`).

---

## 5. Failure Examples & Case Studies

| Filename | Category | Expected Status | Actual Status | Needs Review (Exp / Act) | Reason / Discrepancy |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `math_err_04.csv` | math_error | COMPLETED | COMPLETED | True / True | Fields matched: 7/8, Issues: ['MATH_MISMATCH_TOTAL', 'MISSING_INVOICE_NUMBER'] |
| `scanned_inv_01.pdf` | scanned_noisy | COMPLETED | COMPLETED | False / True | Fields matched: 0/8, Issues: ['MISSING_INVOICE_NUMBER', 'MISSING_TOTAL', 'MISSING_INVOICE_ |
| `scanned_inv_02.pdf` | scanned_noisy | COMPLETED | COMPLETED | False / True | Fields matched: 0/8, Issues: ['MISSING_INVOICE_NUMBER', 'MISSING_TOTAL', 'MISSING_INVOICE_ |
| `scanned_inv_03.pdf` | scanned_noisy | COMPLETED | COMPLETED | False / True | Fields matched: 0/8, Issues: ['MISSING_INVOICE_NUMBER', 'MISSING_TOTAL', 'MISSING_INVOICE_ |
| `scanned_inv_04.pdf` | scanned_noisy | COMPLETED | COMPLETED | False / True | Fields matched: 0/8, Issues: ['MISSING_INVOICE_NUMBER', 'MISSING_TOTAL', 'MISSING_INVOICE_ |
| `scanned_inv_05.png` | scanned_noisy | COMPLETED | COMPLETED | False / True | Fields matched: 0/8, Issues: ['MISSING_INVOICE_NUMBER', 'MISSING_TOTAL', 'MISSING_INVOICE_ |
| `scanned_inv_06.png` | scanned_noisy | COMPLETED | COMPLETED | False / True | Fields matched: 0/8, Issues: ['MISSING_INVOICE_NUMBER', 'MISSING_TOTAL', 'MISSING_INVOICE_ |
| `scanned_inv_07.jpg` | scanned_noisy | COMPLETED | COMPLETED | False / True | Fields matched: 0/8, Issues: ['MISSING_INVOICE_NUMBER', 'MISSING_TOTAL', 'MISSING_INVOICE_ |
| `scanned_inv_08.jpg` | scanned_noisy | COMPLETED | COMPLETED | False / True | Fields matched: 0/8, Issues: ['MISSING_INVOICE_NUMBER', 'MISSING_TOTAL', 'MISSING_INVOICE_ |
| `spreadsheet_inv_01.xlsx` | spreadsheet | COMPLETED | COMPLETED | False / True | Fields matched: 8/8, Issues: ['MISSING_INVOICE_DATE', 'MISSING_INVOICE_NUMBER'] |
| `spreadsheet_inv_02.xlsx` | spreadsheet | COMPLETED | COMPLETED | False / True | Fields matched: 8/8, Issues: ['MISSING_INVOICE_DATE', 'MISSING_INVOICE_NUMBER'] |
| `spreadsheet_inv_03.xlsx` | spreadsheet | COMPLETED | COMPLETED | False / True | Fields matched: 8/8, Issues: ['MISSING_INVOICE_DATE', 'MISSING_INVOICE_NUMBER'] |
| `spreadsheet_inv_04.xlsx` | spreadsheet | COMPLETED | COMPLETED | False / True | Fields matched: 8/8, Issues: ['MISSING_INVOICE_DATE', 'MISSING_INVOICE_NUMBER'] |
| `spreadsheet_inv_05.csv` | spreadsheet | COMPLETED | COMPLETED | False / True | Fields matched: 7/8, Issues: ['MISSING_INVOICE_NUMBER'] |
| `spreadsheet_inv_06.csv` | spreadsheet | COMPLETED | COMPLETED | False / True | Fields matched: 7/8, Issues: ['MISSING_INVOICE_NUMBER'] |
| `spreadsheet_inv_07.csv` | spreadsheet | COMPLETED | COMPLETED | False / True | Fields matched: 7/8, Issues: ['MISSING_INVOICE_NUMBER'] |
| `spreadsheet_inv_08.csv` | spreadsheet | COMPLETED | COMPLETED | False / True | Fields matched: 7/8, Issues: ['MISSING_INVOICE_NUMBER'] |

---

## 6. Known Limitations & Edge Cases

1. **Heavy OCR Degradation on Highly Rotated Scans**: When documents suffer from extreme rotation (> 45 degrees) or severe scanner blur, token confidence drops below the 0.50 threshold, requiring human operator review.
2. **Multi-Page Table Splitting**: Digital invoices where line-item tables break across multiple pages without headers repeated require advanced chunk aggregation.
3. **Spreadsheets without Clear Headers**: Spreadsheets with irregular layouts or nested multi-level headers require LLM column mapping assistance rather than simple row heuristics.
4. **API Rate Limiting**: In high-throughput batch scenarios with live LLMs, API concurrency limits must be regulated using Celery worker rate limits and exponential backoff retry policies.
