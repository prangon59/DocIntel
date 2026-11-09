# AI-Assisted Development Disclosure

## Tools Used
- **Google Antigravity**: Primary agentic AI coding environment for paired architecture planning, iterative phase-by-phase implementation, test-driven validation, and terminal execution.
- **Google Gemini Models**:
  - `gemini-2.5-flash`: Production LLM client for structured invoice field extraction and LLM-assisted spreadsheet column header mapping.
  - `text-embedding-004`: Vector embedding model for page text indexing and hybrid semantic search.
- **Claude**: Architectural planning, prompt engineering review, and verification design.

---

## What AI Generated
1. **System Architecture & Boilerplate**: Initial FastAPI application structure, async SQLAlchemy models, Alembic migration scripts, and `docker-compose.yml` multi-container topology.
2. **Data Schemas**: Pydantic v2 validation models (`InvoiceExtractionSchema`, `StringEvidence`, `DecimalEvidence`, `DateEvidence`, `SpreadsheetColumnMapping`).
3. **Core Services**:
   - Magic-byte file format detection and PyMuPDF text extractor.
   - OpenCV deskewing, Otsu binarization, and Tesseract OCR fallback wrapper.
   - Gemini LLM structured output client with exponential backoff retries.
   - Deterministic financial validation engine and Rapidfuzz duplicate invoice detection.
   - Hybrid search engine combining PostgreSQL `tsvector` full-text search with pgvector cosine distance embeddings via Reciprocal Rank Fusion ($k=60$).
   - Cross-verification service reconciling PDF and Excel documents.
4. **Synthetic Evaluation Dataset**: Generator script `eval/generate_dataset.py` creating 36 diverse synthetic documents (clean PDFs, noisy scans, spreadsheets, deliberate errors, corrupted binaries) with paired ground-truth JSON files.
5. **Benchmark Runner**: `eval/run_eval.py` executing the pipeline and calculating measured field accuracy, line item precision/recall, latencies, and validation metrics.
6. **Frontend UI**: Next.js App Router dashboard, drag-and-drop document uploader, inspection viewer with PDF rendering, editable fields with audit trail, and hybrid search interface.
7. **Test Suites**: 78 unit and integration tests across all services and failure cases.

---

## What Was Reviewed, Tested, and Modified with Human Oversight
1. **Financial Decimal Enforcement**: Ensured all currency and monetary calculations strictly utilize Python `Decimal` rather than binary `float` to eliminate precision rounding errors.
2. **Deterministic Validation Boundary**: Enforced that LLMs are never used for arithmetic verification, duplicate checks, or missing field validations; all checks run strictly through deterministic Python code.
3. **Magic-Byte Sniffing Integrity**: Verified that file detection uses deep binary signatures rather than untrusted client extensions or MIME headers, correctly rejecting spoofed ZIP/XLSX binaries and empty files.
4. **Tolerance Adjustments**: Tuned math validation tolerances to prevent false positives on rounding splits ($0.01 threshold).
5. **Deduplication Thresholding**: Adjusted Rapidfuzz fuzzy string matching to handle supplier name abbreviations (e.g., "TechCorp Intl" vs "TechCorp International") using `max(token_sort_ratio, token_set_ratio) >= 80`.
6. **Error Isolation in Celery Pipeline**: Confirmed that a single malformed file or unreadable page never crashes a batch or worker process; failures are cleanly caught, persisted as `FAILED`, and recorded in `processing_events`.
7. **Strict Evaluation Honesty**: Verified that all numbers in `eval/report.md` are 100% computed from the automated benchmark runner without manual manipulation or fabrication.
