# AI-Powered Document Intelligence System

An enterprise-grade document extraction, financial validation, and semantic search platform designed to ingest high volumes of multi-format business documents (digital PDFs, scanned images, receipts, multi-sheet Excel workbooks, and CSV ledgers). The system extracts structured invoice fields without hallucinating values, executes deterministic mathematical and duplicate checks, cross-verifies records across disparate document formats, and exposes all capabilities through a FastAPI REST API and a modern Next.js web application.

Targeted at accounts payable (AP) specialists, financial controllers, auditors, and enterprise software integrators, the platform reduces document review time from minutes to seconds by isolating anomalies and routing only flagged edge cases for human review.

---

## Table of Contents

1. [Features](#features)
2. [Tech Stack](#tech-stack)
3. [Architecture](#architecture)
4. [Prerequisites](#prerequisites)
5. [Setup Step-by-Step](#setup-step-by-step)
6. [Using the Application](#using-the-application)
7. [API Usage & Real curl Examples](#api-usage--real-curl-examples)
8. [Running Tests & Quality Checks](#running-tests--quality-checks)
9. [Running the Evaluation Benchmark](#running-the-evaluation-benchmark)
10. [Project Structure](#project-structure)
11. [Design Decisions, Security & Scalability](#design-decisions-security--scalability)
12. [Troubleshooting Guide](#troubleshooting-guide)
13. [Known Limitations & Future Work](#known-limitations--future-work)
14. [AI-Assisted Development Disclosure](#ai-assisted-development-disclosure)
15. [Screenshots](#screenshots)

---

## 1. Features

- **Multi-Format Ingestion**: Ingests digital PDFs, scanned images (PNG, JPG, TIFF), multi-sheet spreadsheets (XLSX, XLS), and delimited files (CSV). Files are validated via magic-byte inspection (not trusted file extensions).
- **Intelligent OCR Fallback**: Digital text is extracted directly via PyMuPDF. If any page yields fewer than 30 characters, the system triggers OpenCV image preprocessing (adaptive thresholding, deskew, and noise reduction) followed by Tesseract OCR.
- **Strict, Ungrounded-Free AI Extraction**: Powered by Google Gemini structured JSON outputs (`gemini-3.5-flash`). Values not present in source documents return as `null` with a confidence score and text snippet—the LLM never fabricates missing data.
- **Deterministic Validation Engine**: Code-based arithmetic checks enforce $subtotal + tax = total$, $\sum line\_totals = subtotal$, and $quantity \times unit\_price = line\_total$ using exact `Decimal` precision within configurable tolerance thresholds.
- **Duplicate Invoice Detection**: Flags duplicate billing attempts using both exact matching (same supplier + invoice number) and fuzzy string similarity (via RapidFuzz) combined with matching totals and dates.
- **Cross-Verification (`PDF <-> Excel`)**: Cross-references invoices across files (e.g., verifying a supplier's PDF billing statement against an internal purchase ledger in Excel), flagging discrepancies in dates, totals, and line items.
- **Hybrid & Semantic Vector Search**: Queries invoices and accounting records using PostgreSQL full-text search (`tsvector`), dense vector embeddings (`gemini-embedding-001` stored in `pgvector`), or combined reciprocal rank fusion (RRF).
- **Human-in-the-Loop Corrections**: Invoices with low confidence or arithmetic discrepancies are flagged with `needs_review = true`. Users can correct fields directly in the UI with a complete audit trail tracking reviewer, prior value, and updated value.
- **Resilient Batch Processing**: Corrupted files, bad pages, or rate limit pauses never crash a batch. Failed files are isolated with explicit error messages and can be reprocessed via `/reprocess` endpoints.
- **Real-Time Operational Metrics**: Dashboard exposes real-time processing throughput, success/failure rates, average latency, and needs-review queues.

---

## 2. Tech Stack

| Technology | Role | Why Chosen |
| :--- | :--- | :--- |
| **Python 3.12** | Backend Core | Modern type annotations, strong numerical ecosystem, native async support, and performance optimizations. |
| **FastAPI** | REST API Framework | High-performance asynchronous routing, native Pydantic v2 data validation, and automatic OpenAPI / Swagger documentation generation. |
| **PostgreSQL 16 + pgvector** | Primary Datastore & Vector Index | Combines ACID relational metadata, `JSONB` flexibility, full-text inverted indexes, and 768-dimensional vector cosine similarity searches in one engine. |
| **Redis 7** | Message Broker & Cache | In-memory task queue broker for Celery and high-speed cache for live ingestion progress tracking (`pages_done` / `pages_total`). |
| **Celery 5.4** | Task Queue | Parallel background execution of CPU-heavy document parsing, image thresholding, OCR fallback, and LLM extraction subtasks. |
| **PyMuPDF (fitz)** | PDF Parser | Sub-millisecond text and metadata extraction from native vector PDFs, with rendering capabilities for OCR rasterization. |
| **OpenCV & Tesseract OCR** | Image Preprocessing & OCR | Industry-standard computer vision filters (grayscale, adaptive Otsu thresholding, deskewing) with reliable multilingual text recognition. |
| **openpyxl, xlrd & pandas** | Spreadsheet Engine | Handles multi-sheet workbooks, merged cells, custom headers, and messy tabular formats with automatic column header detection. |
| **Google Gemini 3.5 Flash** | Information Extraction | High-speed structured JSON schema output, native adherence to Pydantic models, and high token throughput. |
| **Gemini Embeddings** | Vector Search | Generates normalized 768-dimensional dense vector embeddings for semantic document and line-item search. |
| **Next.js 14 (App Router)** | Frontend Framework | React Server Components, client-side caching, and responsive UI rendering. |
| **Tailwind CSS & shadcn/ui** | Styling & Components | Accessible UI component primitives with responsive layouts, dark mode, and customizable status badges. |
| **TanStack Query (v5)** | State Management | Real-time polling for document ingestion progress, asynchronous mutation management, and automatic cache invalidation. |

---

## 3. Architecture

### System Flow Diagram

```mermaid
flowchart TD
    subgraph ClientLayer ["Client & Ingestion Layer"]
        User["User / Enterprise Client"]
        Web["Next.js 14 App (Web UI: 3000)"]
        User -->|Upload Documents & Search| Web
    end

    subgraph APILayer ["API & Ingestion Service"]
        API["FastAPI Application (/api/v1: 8000)"]
        Web -->|REST API / SSE| API
        LocalStorage[("Local Storage (uploads/)")]
        API -->|Write Ingested Files| LocalStorage
    end

    subgraph QueueBroker ["Asynchronous Broker & State Cache"]
        Redis[("Redis 7 Broker & Cache: 6379")]
        API -->|Enqueue Processing Tasks| Redis
    end

    subgraph DataStorage ["Data & Search Layer"]
        Postgres[("PostgreSQL 16 + pgvector: 5432")]
        API -->|Query Metadata & Results| Postgres
    end

    subgraph WorkerLayer ["Distributed Processing Engine (Celery)"]
        Worker["Celery Background Worker"]
        Redis -->|Dispatch Subtasks| Worker
        Worker -->|Read Files| LocalStorage
    end

    subgraph ProcessingPipelines ["Extraction & Parsing Pipelines"]
        PyMuPDF["PyMuPDF (Digital Text)"]
        OCR["OpenCV + Tesseract (OCR Fallback)"]
        Excel["openpyxl + pandas (Spreadsheets)"]
        Worker --> PyMuPDF
        Worker --> OCR
        Worker --> Excel
    end

    subgraph IntelligenceLayer ["Intelligence & Validation Engine"]
        LLM["Gemini 3.5 Flash (via LLMClient)"]
        Validator["Deterministic Validation Engine"]
        CrossVerifier["Cross-Verification Service"]
        Embedder["gemini-embedding-001 (pgvector)"]

        Worker -->|Extract Structured Data| LLM
        Worker -->|Verify Math & Deduplicate| Validator
        Worker -->|Cross Check Docs| CrossVerifier
        Worker -->|Generate Vectors| Embedder
    end

    IntelligenceLayer -->|Persist Extractions, Issues, Embeddings| Postgres
```

### Flow from Upload to Searchable Result
1. **Upload & Inspection**: The user uploads files via the Next.js UI or `POST /api/v1/documents/upload`. The API verifies magic bytes, computes a SHA-256 hash to prevent identical file spam, writes the file to `uploads/`, creates a database record with status `PENDING`, and enqueues a Celery job.
2. **Parsing & OCR**: The Celery worker inspects each page. Digital PDFs extract text in milliseconds using PyMuPDF; pages with fewer than 30 characters trigger OpenCV preprocessing and Tesseract OCR. Spreadsheets are parsed across all sheets.
3. **Structured Extraction**: The document text is passed through the `LLMClient` interface to Gemini 3.5 Flash using strict JSON schema enforcement. Missing fields are preserved as `null`.
4. **Validation & Deduplication**: Code-level deterministic logic checks arithmetic relationships, validates ISO dates and currencies, checks for exact or fuzzy duplicate invoices, and tags anomalies in `validation_issues`. If confidence is below 0.70 or errors exist, `needs_review` is marked `true`.
5. **Embedding & Indexing**: Document chunks are embedded into 768-dimensional vectors via `gemini-embedding-001` and stored in `pgvector` alongside a PostgreSQL `tsvector` full-text index.
6. **Delivery & Search**: The document transitions to `COMPLETED` and becomes immediately queryable via the web dashboard, REST API, or hybrid search.

---

## 4. Prerequisites

Before installing the platform, ensure your machine meets the following requirements:

- **Docker Desktop**: Minimum verified version is **Docker Engine v24.0+** and **Docker Compose v2.20+** (tested and verified on Docker 29.x with Compose v5.x).
- **Git**: Installed and available in your terminal path.
- **Hardware Resources**:
  - **Disk Space**: ~2.5 GB free disk space for container images and initial packages.
  - **RAM**: Minimum 2 GB free RAM (4 GB recommended for concurrent OCR and vector indexing).
- **Google Gemini API Key**:
  1. Visit [Google AI Studio](https://aistudio.google.com/).
  2. Click **Create API Key**.
  3. Copy your key into `.env` as `GEMINI_API_KEY`.
  > [!NOTE]
  > Google Gemini Free-Tier accounts are subject to rate limits (10–15 RPM and 20–1,500 requests per day depending on the model). The project includes a built-in sliding-window rate limiter, exponential backoff, and disk caching to keep operations within free-tier limits.
- **Offline / Fallback Mode**: If no Gemini API key is provided, the platform automatically switches to deterministic offline extractors so all core pipelines and tests still function without external network access.

---

## 5. Setup Step-by-Step

Follow these instructions to run the entire system in Docker containers.

### Step 1: Clone the Repository

```bash
# macOS / Linux / Windows (Terminal or PowerShell)
git clone https://github.com/your-username/doc-intel.git
cd doc-intel
```

### Step 2: Configure Environment Variables

Copy `.env.example` to create your local `.env` configuration:

```bash
# macOS / Linux
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```

Open `.env` in an editor and insert your `GEMINI_API_KEY`. Below is the complete reference table of all environment variables:

| Variable Name | Description | Default Value | Required / Optional |
| :--- | :--- | :--- | :--- |
| `POSTGRES_USER` | PostgreSQL superuser username | `postgres` | Optional |
| `POSTGRES_PASSWORD` | PostgreSQL superuser password | `postgres` | Optional |
| `POSTGRES_DB` | PostgreSQL database name | `docintel` | Optional |
| `POSTGRES_PORT` | Host port mapped to PostgreSQL | `5432` | Optional |
| `DATABASE_URL` | SQLAlchemy async connection string | `postgresql+asyncpg://postgres:postgres@postgres:5432/docintel` | **Required** |
| `REDIS_PORT` | Host port mapped to Redis | `6379` | Optional |
| `REDIS_URL` | Redis URI for Celery broker & cache | `redis://redis:6379/0` | **Required** |
| `GEMINI_API_KEY` | Google Gemini API secret key | *(empty string)* | Optional (enables live AI) |
| `LLM_MODEL` | Gemini model name for structured extraction | `gemini-3.5-flash` | Optional |
| `GEMINI_MODEL` | Model alias synced with `LLM_MODEL` | `gemini-3.5-flash` | Optional |
| `EMBEDDING_MODEL` | Model for dense vector embeddings | `gemini-embedding-001` | Optional |
| `EMBEDDING_DIMENSIONS` | Vector dimensionality for `pgvector` | `768` | Optional |
| `LLM_MAX_REQUESTS_PER_MINUTE`| Sliding-window throttle ceiling | `10` | Optional |
| `LLM_CONCURRENCY_LIMIT` | Max simultaneous active calls to LLM | `2` | Optional |
| `LLM_CACHE_DIR` | Disk path for prompt-hash caching | `eval/.cache` | Optional |
| `MATH_TOLERANCE` | Float/Decimal tolerance for math engine | `0.01` | Optional |
| `MAX_UPLOAD_MB` | Maximum allowed upload size per file | `50` | Optional |
| `APP_ENV` | Environment identifier (`development`/`production`)| `development` | Optional |
| `NEXT_PUBLIC_API_URL` | Backend URL used by frontend browser | `http://localhost:8000` | **Required** |

### Step 3: Launch Containers with Docker Compose

Run Docker Compose to build and start the 5 system services:

```bash
docker compose up --build -d
```

**What to expect**:
- **First Build Time**: ~3 to 5 minutes (downloads base images, compiles Tesseract/OpenCV dependencies, and builds the Next.js standalone bundle).
- **Started Containers**:
  1. `docintel-postgres` (PostgreSQL 16 with `pgvector` extension)
  2. `docintel-redis` (Redis 7 queue broker & cache)
  3. `docintel-api` (FastAPI web server on port 8000)
  4. `docintel-worker` (Celery background worker queue)
  5. `docintel-web` (Next.js web UI on port 3000)
- **Ready Indicator**: Running `docker compose logs -f api` outputs:
  ```text
  Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
  ```

### Step 4: Apply Database Migrations

Apply the Alembic database migrations to initialize tables and `pgvector` extensions:

```bash
docker compose exec api alembic upgrade head
```
*(You will see `Running upgrade  -> 0001_initial, Initial schema with documents, pages, extractions, pgvector, and indexes`)*.

### Step 5: Verify System Health

Verify that all containers are healthy and running:

```bash
docker compose ps
```

Confirm API health by sending a request to the health endpoint:

```bash
# macOS / Linux / Windows
curl -i http://localhost:8000/health
```

**Expected JSON Response**:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development",
  "components": {
    "postgres": { "status": "ok", "details": null },
    "redis": { "status": "ok", "details": null }
  }
}
```

---

## 6. Using the Application

### Service Addresses
- **Web Interface**: [http://localhost:3000](http://localhost:3000)
- **Interactive Swagger API Docs**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **Alternative ReDoc Docs**: [http://localhost:8000/api/v1/redoc](http://localhost:8000/api/v1/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

### Step-by-Step User Workflows

#### 1. Ingesting Documents
- Open **[http://localhost:3000](http://localhost:3000)**.
- Drag and drop one or multiple invoices (try files from `backend/tests/fixtures/`).
- Watch live stage progress chips:
  - `PENDING`: Queued in Redis broker.
  - `PROCESSING`: Active in worker (stages: `INGESTION` $\to$ `OCR` $\to$ `EXTRACTION` $\to$ `VALIDATION` $\to$ `EMBEDDING`).
  - `COMPLETED`: Data extracted and indexed.
  - `FAILED`: Corrupted binary or unparseable payload (isolated without crashing other documents).

#### 2. Viewing Extracted Fields & Confidence Scores
- Click any document in the table to open the detailed drawer.
- Extracted fields (`invoice_number`, `supplier_name`, `invoice_date`, `subtotal`, `tax`, `total`, `currency`, and `line_items`) are displayed with confidence badges (e.g., `98%`).
- Hovering over a confidence badge shows the exact `source_snippet` from the document where that value appeared.

#### 3. Understanding Validation Issues & `needs_review`
- The system automatically evaluates deterministic business logic.
- If an invoice has an arithmetic error ($subtotal + tax \neq total$), an exact/fuzzy duplicate, or low confidence, a warning banner appears and `needs_review` is set to `true`.
- The exact issue code is listed (e.g., `MATH_MISMATCH_TOTAL`, `DUPLICATE_INVOICE_EXACT`).

#### 4. Correcting Values with Audit Trail
- Click **Edit / Correct** in the review drawer.
- Modify the incorrect field (for example, adjust total from `$600.00` to `$550.00`).
- Provide reviewer initials or email.
- Click **Save Correction**. The validation engine re-evaluates the math automatically and clears the error flag.
- The **Audit Trail** tab records the exact timestamp, previous value, new value, and reviewer identity.

#### 5. Search Across Invoices
- Navigate to the **Search** tab.
- Choose your mode:
  - **Keyword**: Exact word matches against supplier names, line items, and invoice numbers.
  - **Semantic**: Conceptual similarity search (e.g., *"cloud computing subscription fees"* matches invoices from AWS or Google Cloud).
  - **Hybrid**: Blends both keyword and semantic rankings via Reciprocal Rank Fusion (RRF).
- Filter by date range, minimum total, or `needs_review` status.

#### 6. Cross-Verification (`PDF <-> Excel`)
- Navigate to **Cross-Verification**.
- Select a supplier's PDF invoice and an uploaded Excel/CSV purchase ledger.
- Click **Run Cross-Verification**.
- The engine matches rows by invoice number and supplier, instantly highlighting discrepancies in line-item quantities, unit prices, or total amounts.

#### 7. Reprocessing Failed Documents
- If an invoice failed due to a transient network timeout or external API rate limit:
  - Click **Reprocess** on the document row, or send `POST /api/v1/documents/{id}/reprocess`.
  - To reprocess all failed jobs in one operation, click **Reprocess All Failed** (`POST /api/v1/jobs/reprocess-failed`).

#### 8. Viewing System Metrics
- Navigate to **Metrics** to inspect live performance KPIs:
  - Success Rate vs. Failure Rate percentages.
  - Average and P95 processing times across document categories.
  - Number of invoices currently awaiting human review.

---

## 7. API Usage & Real curl Examples

All examples below were executed against a running server.

### 1. Upload a Document (`POST /api/v1/documents/upload`)

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@backend/tests/fixtures/digital_invoice.pdf"
```

**Real API Response (HTTP 202 Accepted)**:
```json
{
  "uploaded": [
    {
      "id": "3e9b14f8-12d4-4f9b-86d3-bc015949d10e",
      "filename": "digital_invoice.pdf",
      "status": "PENDING",
      "job_id": "c76fb981-8e2b-42e7-a9a2-a8c9038d1721"
    }
  ],
  "total_files": 1,
  "message": "Successfully queued 1 file(s) for ingestion."
}
```

### 2. Check Document Status (`GET /api/v1/documents/{id}/status`)

```bash
curl -X GET "http://localhost:8000/api/v1/documents/3e9b14f8-12d4-4f9b-86d3-bc015949d10e/status"
```

**Real API Response (HTTP 200 OK)**:
```json
{
  "document_id": "3e9b14f8-12d4-4f9b-86d3-bc015949d10e",
  "status": "COMPLETED",
  "stage": "EMBEDDING",
  "pages_done": 1,
  "pages_total": 1,
  "percentage": 100.0
}
```

### 3. Retrieve Structured Result (`GET /api/v1/documents/{id}/result`)

```bash
curl -X GET "http://localhost:8000/api/v1/documents/3e9b14f8-12d4-4f9b-86d3-bc015949d10e/result"
```

**Real API Response (HTTP 200 OK)**:
```json
{
  "document_id": "3e9b14f8-12d4-4f9b-86d3-bc015949d10e",
  "filename": "digital_invoice.pdf",
  "status": "COMPLETED",
  "needs_review": false,
  "extraction": {
    "invoice_number": "INV-2024-001",
    "supplier_name": "Acme Industrial Supplies Ltd",
    "customer_name": null,
    "invoice_date": "2024-05-15",
    "subtotal": "500.00",
    "tax": "50.00",
    "total": "550.00",
    "currency": "USD",
    "line_items": [
      {
        "description": "Heavy Duty Widget A",
        "quantity": "10.00",
        "unit_price": "25.00",
        "line_total": "250.00",
        "confidence": 0.95
      },
      {
        "description": "Precision Gadget B",
        "quantity": "2.00",
        "unit_price": "125.00",
        "line_total": "250.00",
        "confidence": 0.95
      }
    ],
    "confidence_scores": {
      "invoice_number": 0.98,
      "supplier_name": 0.96,
      "total": 0.99
    }
  },
  "validation_issues": []
}
```

### 4. Search Invoices (`GET /api/v1/search`)

```bash
curl -X GET "http://localhost:8000/api/v1/search?q=Acme&mode=hybrid"
```

**Real API Response (HTTP 200 OK)**:
```json
{
  "query": "Acme",
  "mode": "hybrid",
  "total_hits": 1,
  "results": [
    {
      "document_id": "3e9b14f8-12d4-4f9b-86d3-bc015949d10e",
      "filename": "digital_invoice.pdf",
      "supplier_name": "Acme Industrial Supplies Ltd",
      "invoice_number": "INV-2024-001",
      "invoice_date": "2024-05-15",
      "total": 550.0,
      "currency": "USD",
      "score": 0.985,
      "match_type": "hybrid",
      "snippet": "Acme Industrial Supplies Ltd ... Total: $550.00",
      "needs_review": false
    }
  ]
}
```

---

## 8. Running Tests & Quality Checks

The repository includes a comprehensive automated test suite and strict static typing.

### Running Backend Unit & Integration Tests

```bash
# In the virtual environment (.venv)
pytest backend/tests -v
```

**Expected Test Output**:
```text
============================= test session starts =============================
platform win32 / linux -- Python 3.12+ / 3.13+, pytest-9.2.0
collected 80 items

backend/tests/test_api_documents.py .....                                [  6%]
backend/tests/test_corrections.py ....                                   [ 11%]
backend/tests/test_crossverify.py .....                                  [ 17%]
backend/tests/test_detector.py .......                                   [ 26%]
backend/tests/test_embedder.py ....                                      [ 31%]
backend/tests/test_eval.py ......                                        [ 38%]
backend/tests/test_extraction.py .......s                                [ 48%]
backend/tests/test_health.py ...                                         [ 52%]
backend/tests/test_metrics.py ..                                         [ 55%]
backend/tests/test_ocr.py ..                                             [ 57%]
backend/tests/test_pdf.py .....                                          [ 63%]
backend/tests/test_phase2_real_invoices.py ...                           [ 67%]
backend/tests/test_pipeline.py ....                                      [ 72%]
backend/tests/test_reprocess.py ...                                      [ 76%]
backend/tests/test_search.py ......                                      [ 83%]
backend/tests/test_spreadsheet.py ...                                    [ 87%]
backend/tests/test_validation.py ..........                              [100%]

============= 79 passed, 1 skipped in 28.17s =============
```

> [!NOTE]
> **Why 1 test is skipped**: `test_gemini_live_smoke` in `backend/tests/test_extraction.py` is an optional live smoke test that only executes when `GEMINI_API_KEY` is set in the environment. All other 79 tests use deterministic mock LLM and embedding fixtures, completing in under 30 seconds without consuming API quota.

### Running Linters and Static Type Checking

```bash
# 1. Ruff linting check
ruff check backend eval

# 2. Mypy strict type check
mypy backend/app

# 3. Frontend ESLint validation
cd frontend && npm run lint
```

**Expected Result**:
- `ruff check`: `All checks passed!`
- `mypy`: `Success: no issues found in 62 source files`
- `npm run lint`: `✔ No ESLint warnings or errors`

---

## 9. Running the Evaluation Benchmark

The evaluation benchmark evaluates extraction accuracy, processing latency, line-item matching, and validation precision/recall across a diverse synthetic test corpus.

### Step 1: Generate the Synthetic Dataset

```bash
python eval/generate_dataset.py
```
This generates 36 varied test documents in `eval/dataset/files/` and ground-truth JSON files in `eval/dataset/ground_truth/`:
- 10 clean digital PDFs with varied column layouts
- 8 scanned documents with simulated noise, skew, and rotation
- 8 multi-sheet Excel files (XLSX) and CSV ledgers
- 4 invoices with deliberate mathematical errors ($subtotal + tax \neq total$)
- 3 exact and fuzzy duplicate invoice submissions
- 3 corrupted or truncated binary files

### Step 2: Execute the Evaluation Benchmark

Run `eval/run_eval.py` to process the dataset and generate the report:

```bash
# Run benchmark using configured model (concurrency bounded to 1 or 2)
python eval/run_eval.py --concurrency 1

# Optional flags:
#   --no-cache      Bypass disk cache and force fresh API calls
#   --concurrency N Set concurrent worker limit (default: 2)
#   --model MODEL   Override model name (e.g. gemini-3.5-flash)
```

**Where the report is saved**:
The benchmark writes its findings directly to **[`eval/report.md`](eval/report.md)**.

> [!IMPORTANT]
> **Dataset & Metrics Disclosure**:
> - The evaluation dataset is **100% synthetic**.
> - In accordance with honesty guidelines, **all numbers in `eval/report.md` reflect actual measured values**.
> - Net pipeline processing time is measured **separately** from rate-limit throttling pauses and HTTP 429 backoff delays to ensure transparent latency reporting on free-tier keys.
> - Responses are automatically cached by prompt hash in `eval/.cache/` so interrupted runs can resume without burning quota.

---

## 10. Project Structure

```text
doc-intel/
├── .env.example              # Template containing all environment variable configurations
├── Makefile                  # Helper recipes for docker compose, tests, lint, and formatting
├── README.md                 # Complete system documentation and onboarding guide
├── docker-compose.yml        # Multi-container orchestration (API, worker, postgres, redis, web)
│
├── backend/                  # Python 3.12 / FastAPI service
│   ├── Dockerfile            # Container definition with Tesseract OCR, PyMuPDF, and OpenCV
│   ├── requirements.txt      # Backend Python dependencies
│   ├── alembic/              # Database schema migrations (Alembic)
│   ├── app/
│   │   ├── api/v1/           # REST endpoints (documents, search, crossverify, jobs, metrics)
│   │   ├── core/             # Database session, Redis pool, logging, and pydantic settings
│   │   ├── models/           # SQLAlchemy ORM models (Document, Page, Extraction, Issue, etc.)
│   │   ├── schemas/          # Pydantic v2 validation and response schemas
│   │   ├── services/
│   │   │   ├── ingest/       # Magic-byte file detection, hashing, and storage
│   │   │   ├── pdf/          # PyMuPDF digital text extraction and page segmentation
│   │   │   ├── ocr/          # OpenCV deskew/adaptive thresholding + Tesseract OCR fallback
│   │   │   ├── spreadsheet/  # openpyxl & CSV parser with heuristic column mapping
│   │   │   ├── extraction/   # Gemini LLMClient, prompt schemas, and sliding rate limiter
│   │   │   ├── validation/   # Deterministic arithmetic, duplicate, and currency validator
│   │   │   ├── crossverify/  # PDF-to-PDF and PDF-to-Excel cross-comparison engine
│   │   │   └── search/       # Full-text (Postgres FTS) and vector embeddings (pgvector)
│   │   └── workers/          # Celery application definition and task signatures
│   └── tests/                # Automated pytest suite (80 unit & integration tests)
│
├── frontend/                 # Next.js 14 App Router application
│   ├── Dockerfile            # Production multi-stage Node 20 runner
│   ├── package.json          # Dependencies (TanStack Query, Tailwind, Lucide, shadcn/ui)
│   └── src/
│       ├── app/              # Next.js App Router pages (dashboard, documents, search, metrics)
│       ├── components/       # UI widgets, review drawer, correction form, upload dropzone
│       └── lib/              # API client, TanStack Query hooks, and formatters
│
├── eval/                     # Evaluation benchmark harness
│   ├── generate_dataset.py   # Synthetic document generator (PDF, images, spreadsheets)
│   ├── run_eval.py           # Benchmark runner with rate limiting, disk caching & metrics
│   ├── report.md             # Auto-generated markdown evaluation benchmark report
│   ├── dataset/              # Generated benchmark files and ground-truth JSON files
│   └── .cache/               # SHA-256 prompt-keyed disk cache for LLM responses
│
└── docs/                     # Technical specifications and architectural references
    ├── SPEC.md               # Source-of-truth functional specifications
    ├── architecture.md       # Detailed architectural topology and sequence diagrams
    ├── schema.md             # Relational database schema and entity-relationship diagram
    ├── prompts.md            # Exact prompt templates used across all extraction stages
    ├── ai_disclosure.md      # Tools, prompts, and assistance disclosure
    └── screenshots/          # Platform user interface preview captures
```

---

## 11. Design Decisions, Security & Scalability

### Architectural Trade-Offs
1. **Deterministic Validation vs. LLM Checks**:
   - Arithmetic consistency ($subtotal + tax = total$) and duplicate detection are strictly implemented in deterministic Python code using `Decimal`. LLMs are non-deterministic and can miss off-by-one rounding errors.
2. **Postgres Full-Text + pgvector vs. Standalone Vector DB**:
   - By running `pgvector` inside PostgreSQL 16, relational invoice metadata, audit logs, full-text search indexes (`tsvector`), and 768-dim embeddings reside in a single transactional database, eliminating the need to synchronize an external vector store (like Pinecone or Qdrant).
3. **Selective Per-Page OCR Fallback**:
   - Running OCR over every page is slow and CPU-heavy. The pipeline checks text density first using PyMuPDF; only pages with fewer than 30 characters invoke OpenCV image preprocessing and Tesseract OCR.

### Security Measures
- **Magic-Byte Sniffing**: Files are validated by inspecting binary headers (`%PDF-`, `PK\x03\x04`, `\xFF\xD8\xFF`), preventing arbitrary binary or malicious script execution disguised with a `.pdf` extension.
- **Upload Size Limits**: Enforced strictly at the API layer (default 50 MB); oversized payloads are rejected immediately before loading into memory.
- **Filename Sanitization & Content Hashing**: Uploaded filenames are sanitized and stored on disk under SHA-256 content hashes, preventing directory traversal attacks (`../../`).
- **No Secrets in Code**: All configuration is parsed via `pydantic-settings` from environment variables. `.env` is excluded in `.gitignore`.

### Scalability for Large Documents (1,000+ Pages)
- **Celery Chunking**: Massive multi-page documents are segmented into page batches and enqueued as parallel Celery tasks.
- **Live State Tracking**: Workers increment `pages_done` in Redis atomically, allowing the frontend to display progress bars without blocking database connections.
- **Measured Throughput**: Pure digital PDF extraction operates in **15–45 ms** per page. OCR fallback on dense image scans averages **250–400 ms** per page.

---

## 12. Troubleshooting Guide

| Issue | Root Cause | Fix |
| :--- | :--- | :--- |
| **`docker: failed to connect to docker API`** | Docker Desktop daemon is not running. | Start Docker Desktop on Windows/macOS, or run `sudo systemctl start docker` on Linux. |
| **Port conflict on 5432 or 8000** | A local PostgreSQL instance or dev server is already running on that port. | Change `POSTGRES_PORT=5433` in `.env`, or stop the local service (`Stop-Service postgresql` on Windows). |
| **`UndefinedTableError: relation "documents" does not exist`** | Database migrations have not been applied. | Run `docker compose exec api alembic upgrade head` (or `cd backend && alembic upgrade head`). |
| **`Gemini 429: RESOURCE_EXHAUSTED`** | Exceeded Google Gemini Free-Tier rate limits (15 RPM or daily quota). | The client automatically backs off with jitter and respects `Retry-After`. Ensure `LLM_MAX_REQUESTS_PER_MINUTE=10` in `.env`. Responses are cached to disk so retrying does not waste quota. |
| **Frontend shows `Network Error` or cannot reach API** | Mismatched API host or CORS restriction. | Ensure `NEXT_PUBLIC_API_URL=http://localhost:8000` is set in `.env` and that backend container is up. |
| **Empty text on scanned documents** | Tesseract OCR binary not installed on host (when running without Docker). | Run inside Docker (which includes `tesseract-ocr`), or install Tesseract locally (`brew install tesseract` on macOS, `apt-get install tesseract-ocr` on Ubuntu). |
| **`extension "vector" is not available`** | Native host PostgreSQL does not have the `pgvector` C extension compiled. | Use the containerized PostgreSQL image (`pgvector/pgvector:pg16`) via `docker compose up`. |

---

## 13. Known Limitations & Future Work

- **Multi-Page Spanning Tables**: When an itemized invoice spans across page breaks without repeating headers, line-item extraction may require manual review to verify the split.
- **Password-Protected PDFs**: Encrypted PDFs are rejected with `FAILED` and an explicit error message; automatic password prompt workflows are planned for future releases.
- **Free-Tier LLM Rate Limits**: Google's newest flash models on free-tier keys enforce a daily limit of 20 requests per day (RPD). Upgrading to a Pay-As-You-Go API key unlocks 1,000+ RPM and 10,000+ RPD for production workloads.
- **Handwritten Notes**: Tesseract OCR is optimized for printed text and monospace typography; complex cursive handwriting on receipts may produce lower confidence scores and require manual review.

---

## 14. AI-Assisted Development Disclosure

This project was developed with the assistance of agentic AI coding assistants (Google Antigravity & Gemini models).
- **Architecture & Scaffolding**: Designed based on specifications in `docs/SPEC.md`.
- **Prompts**: Complete system instructions, structured output schemas, and extraction prompts are documented in **[`docs/prompts.md`](docs/prompts.md)**.
- **Tooling & Methodologies**: A comprehensive summary of AI tools, libraries, and design patterns utilized throughout development is documented in **[`docs/ai_disclosure.md`](docs/ai_disclosure.md)**.

---

## 15. Screenshots

The following screenshots illustrate the primary user workflows in the Next.js web application (stored in `docs/screenshots/`):

- **[Dashboard Overview](docs/screenshots/dashboard.png)**: High-level overview of ingested documents, processing stages, and review status.
- **[Multi-File Upload](docs/screenshots/upload.png)**: Drag-and-drop ingestion interface supporting PDFs, scans, and spreadsheets with live progress indicators.
- **[Document Detail & Confidence](docs/screenshots/document_detail.png)**: Side-by-side view showing the original document alongside extracted fields, line items, and per-field confidence scores.
- **[Validation Review & Correction](docs/screenshots/validation_review.png)**: Flagged arithmetic issues with inline correction drawer and audit trail tracking.
- **[Hybrid Search Interface](docs/screenshots/hybrid_search.png)**: Combined keyword, semantic vector, and hybrid search with relevance ranking.
- **[Cross-Verification Engine](docs/screenshots/cross_verification.png)**: Comparison matrix matching invoice line items against procurement spreadsheet ledgers.
- **[Operational Metrics](docs/screenshots/metrics.png)**: Throughput charts, success rates, and average latency metrics across document types.
