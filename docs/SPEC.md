# SPEC: AI-Powered Document Intelligence System

You are a senior AI/full-stack engineer. Build a production-quality system as a monorepo. Work in phases. After each phase, run tests and show an artifact summary before continuing.

## BUSINESS GOAL
Companies receive thousands of business documents (invoices, receipts, scanned PDFs, images, Excel, CSV; PDFs up to ~1000 pages). The system must ingest them, extract structured invoice data, validate it, cross-verify across documents (PDF<->PDF, PDF<->Excel), and expose everything via REST API + a web UI with keyword and semantic search.

## TECH STACK (do not change without asking)
- Backend: Python 3.12, FastAPI, SQLAlchemy 2 (async) + Alembic, Pydantic v2
- Jobs: Celery + Redis (progress updates, retries with exponential backoff)
- DB: PostgreSQL 16 + pgvector (JSONB for results, tsvector for full-text)
- PDF text: PyMuPDF. OCR: Tesseract + OpenCV preprocessing (deskew, denoise, adaptive threshold). Per-page OCR fallback when a PDF page has <30 chars.
- Spreadsheets: pandas + openpyxl + xlrd; handle multiple sheets, detect header rows, skip empty rows, handle merged cells.
- LLM: Gemini 2.5 Flash via API with JSON-schema structured output, wrapped in an `LLMClient` interface so the provider can be swapped. Keys from env vars.
- Embeddings: via an `Embedder` interface; stored in pgvector.
- Frontend: Next.js (App Router) + TypeScript + Tailwind + shadcn/ui + TanStack Query + react-hook-form + zod. Clean, modern, responsive UI with dark mode.
- Infra: Docker Compose (api, worker, postgres, redis, web), .env.example, Makefile.
- Tests: pytest, pytest-asyncio, httpx; ruff + mypy configured.

## REPO STRUCTURE
- /backend (app/api, app/core, app/models, app/schemas, app/services/{ingest,ocr,pdf,spreadsheet,extraction,validation,crossverify,search}, app/workers, tests)
- /frontend
- /eval (labeled dataset generator, ground truth JSON, run_eval.py, report)
- /docs (architecture.md with Mermaid diagram, schema.md, ai_disclosure.md, prompts.md)
- docker-compose.yml, README.md, .env.example

## FUNCTIONAL REQUIREMENTS

### 1. Document processing
- Accept PDF, JPG, PNG, TIFF (multi-page), XLSX, XLS, CSV. Multiple files per upload. Validate by magic bytes, not only extension. Max size configurable.
- Pipeline per file: detect type -> digital PDF text extraction -> OCR for scanned pages/images -> spreadsheet parsing -> normalized PageText records.
- Large PDFs: split into per-page Celery subtasks processed in parallel (chunked), aggregate progress (pages_done/pages_total). Group pages into invoice segments (heuristics: invoice-number / "Invoice" header changes).
- Handle corrupted files, password-protected PDFs, poor image quality (preprocessing + OCR confidence score), empty files. Never crash a batch: mark the file FAILED with a clear error and keep going.

### 2. AI extraction
Extract: invoice_number, invoice_date (ISO 8601), supplier_name, customer_name, subtotal, tax, total, currency (ISO 4217), line_items[{description, quantity, unit_price, line_total}].
- Return strict JSON validated by Pydantic. Money uses Decimal.
- NEVER invent values: missing -> null. Each field has confidence (0-1) and a source_snippet. Grounding check: if the extracted value does not appear in the source text (after normalization), lower confidence and flag.
- Spreadsheet rows map to invoices via a column-mapping step (LLM-assisted header mapping, then deterministic parsing).
- Retries on invalid JSON, token-limit-safe chunking, timeouts.

### 3. Validation (deterministic code, not LLM)
- Missing required fields; invalid dates; negative/non-numeric amounts.
- sum(line_totals) ~= subtotal; subtotal + tax ~= total; quantity*unit_price ~= line_total (configurable tolerance, e.g. 0.01).
- Duplicate detection: same (supplier, invoice_number) or fuzzy match (rapidfuzz) + same total/date.
- Currency consistency.
- Output a list of ValidationIssue{code, severity, field, message}; set needs_review=true if any error-level issue or low confidence.
- Cross-verification: match invoices across documents (PDF<->PDF, PDF<->Excel) by invoice number + supplier; report mismatches in totals/dates/line items.

### 4. Backend API (versioned /api/v1, OpenAPI docs)
- POST /documents/upload (multi-file) -> job ids, returns immediately
- GET /documents (filters: status, supplier, date range, needs_review, pagination, sorting), GET /documents/{id}
- GET /documents/{id}/status (progress, current stage, pages done)
- GET /documents/{id}/result (structured data + validation issues + evidence)
- PATCH /documents/{id}/result (manual corrections, audit history, re-run validation)
- POST /documents/{id}/reprocess and POST /jobs/reprocess-failed
- GET /search?q=&mode=keyword|semantic|hybrid&filters...
- POST /crossverify (document ids) and GET /documents/{id}/crossverify
- GET /metrics (success rate, failure rate, avg processing time)
- GET /health. Consistent error format, request IDs, structured logging, CORS config, rate limiting, upload size limits, input sanitization.

### 5. Database
Tables: documents (metadata, status, hash for dedupe, file_type), pages (text, ocr_confidence, method), extractions (JSONB, confidence, model, prompt_version), line_items, validation_issues, corrections (audit trail), processing_events (history per stage with timings), embeddings (pgvector).
Indexes: GIN on tsvector, ivfflat/hnsw on vectors, btree on supplier/date. Alembic migrations. ERD in docs/schema.md.

### 6. Frontend (modern, polished)
- Drag-and-drop multi-file upload with per-file progress bars; polling or SSE for live status.
- Documents table with filters, status badges, needs-review highlight.
- Detail page: side-by-side original file preview and extracted fields, confidence indicators, validation errors inline, editable fields with save, correction history, line-items table.
- Search page with keyword / semantic / hybrid toggle and highlights.
- Dashboard with metrics cards. Loading skeletons, error toasts, empty states, accessibility basics, responsive layout.

### 7. Testing and evaluation
- Unit tests: PDF extraction, OCR (including a degraded image), spreadsheet parsing (multi-sheet, messy headers), extraction schema (mock LLM), validation rules, duplicate detection, API endpoints, failure scenarios (corrupted file, wrong extension, LLM timeout, empty file).
- /eval: script that GENERATES a labeled synthetic dataset (varied invoice layouts as digital PDF, scanned PDF with noise/rotation, PNG/JPG, XLSX, CSV, plus corrupted files) with ground-truth JSON. run_eval.py runs the real pipeline and reports field-level extraction accuracy, line-item accuracy, avg/p95 processing time, document success rate, failure rate, and validation-flag precision/recall. Output to eval/report.md. Report ONLY actually measured numbers.

## NON-FUNCTIONAL
Type hints everywhere, small single-purpose modules, dependency injection, config via pydantic-settings, no secrets in code, idempotent tasks, graceful shutdown, docstrings on public functions, conventional commits.

## DELIVERABLES
Working app via `docker compose up`, README (setup + design decisions + scalability notes), architecture diagram (Mermaid), DB schema, tests + results, eval report, docs/prompts.md (all LLM prompts used), docs/ai_disclosure.md (AI-assisted development disclosure).

## PHASES
- Phase 0: implementation plan artifact, repo skeleton, docker-compose. Wait for approval.
- Phase 1: DB models, migrations, upload API, file-type validation, Celery pipeline for digital PDFs, images (OCR), spreadsheets, page-level progress. Tests.
- Phase 2: LLM extraction service (structured schema, grounding check, retries), validation engine, duplicate detection. Tests with mocked LLM.
- Phase 3: search (full-text + pgvector + hybrid), corrections with audit trail, reprocess endpoints, cross-verification, metrics endpoint.
- Phase 4: Next.js frontend (upload, status, detail + correction, search, dashboard) with shadcn/ui.
- Phase 5: eval dataset generator, run_eval.py, real evaluation, eval/report.md, README, architecture diagram, docs.
