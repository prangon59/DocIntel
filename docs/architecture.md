# System Architecture: AI Document Intelligence

## Overview

The AI Document Intelligence System is an enterprise-grade document extraction, financial validation, and semantic search platform designed as a decoupled, microservices-ready monorepo comprising:
- **FastAPI Backend (`/backend`)**: High-throughput asynchronous REST API providing file ingestion, document query, result retrieval, manual correction, and search.
- **PostgreSQL 16 + pgvector**: Unified relational metadata store, full-text inverted index (`tsvector`), and high-dimensional vector embeddings for semantic search.
- **Redis 7**: Distributed task queue broker and in-memory cache for ingestion state and live progress counters.
- **Celery Distributed Workers**: Asynchronous, parallel background workers responsible for PDF chunking, OpenCV image preprocessing, Tesseract OCR fallback, spreadsheet parsing, LLM structured extraction, and deterministic validation.
- **Next.js Web Frontend (`/frontend`)**: Modern React interface providing multi-file drag-and-drop ingestion, live page-level progress monitoring, side-by-side inspection with original document rendering, inline validation alerts, editable fields, and hybrid search.

---

## 1. High-Level Architecture Topology

```mermaid
flowchart TD
    subgraph ClientLayer ["Client & Ingestion Layer"]
        User["User / Enterprise Client"]
        Web["Next.js 14 App (Web UI)"]
        User -->|Upload Documents & Search| Web
    end

    subgraph APILayer ["API & Ingestion Service"]
        API["FastAPI Application (/api/v1)"]
        Web -->|REST API / SSE| API
        LocalStorage[("Storage (uploads/)")]
        API -->|Write Ingested Files| LocalStorage
    end

    subgraph QueueBroker ["Asynchronous Broker & State Cache"]
        Redis[("Redis 7 Broker & Cache")]
        API -->|Enqueue Chunked Tasks| Redis
    end

    subgraph DataStorage ["Data & Search Layer"]
        Postgres[("PostgreSQL 16 + pgvector")]
        API -->|Query Metadata & Results| Postgres
    end

    subgraph WorkerLayer ["Distributed Processing Engine (Celery)"]
        Worker1["Celery Worker (PDF & OCR)"]
        Worker2["Celery Worker (Spreadsheet & Extraction)"]
        Redis -->|Dispatch Subtasks| Worker1
        Redis -->|Dispatch Subtasks| Worker2
        Worker1 -->|Read Files| LocalStorage
        Worker2 -->|Read Files| LocalStorage
    end

    subgraph ProcessingPipelines ["Processing Pipelines"]
        PyMuPDF["PyMuPDF (Digital Text)"]
        OCR["OpenCV + Tesseract (OCR Fallback)"]
        Excel["openpyxl + csv (Spreadsheets)"]
        Worker1 --> PyMuPDF
        Worker1 --> OCR
        Worker2 --> Excel
    end

    subgraph IntelligenceLayer ["Intelligence & Validation Engine"]
        LLM["Gemini 2.5 Flash (via LLMClient)"]
        Validator["Deterministic Validation Engine"]
        CrossVerifier["Cross-Verification Service"]
        Embedder["text-embedding-004 (Gemini Embedder)"]

        Worker1 & Worker2 -->|Extract Structured Data| LLM
        Worker1 & Worker2 -->|Verify Math & Deduplicate| Validator
        Worker1 & Worker2 -->|Cross Check Docs| CrossVerifier
        Worker1 & Worker2 -->|Generate Vectors| Embedder
    end

    IntelligenceLayer -->|Persist Extractions, Issues, Embeddings| Postgres
```

---

## 2. Ingestion & Extraction Pipeline Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as Client / User
    participant Frontend as Next.js Web UI
    participant API as FastAPI Ingestion API
    participant Storage as File Storage (uploads/)
    participant Redis as Redis Queue & Cache
    participant Worker as Celery Worker Pipeline
    participant DB as PostgreSQL 16 + pgvector
    participant LLM as Gemini 2.5 Flash / Embedder

    User->>Frontend: Drag-and-drop Invoice (PDF / Scanned / XLSX)
    Frontend->>API: POST /api/v1/documents/upload (multipart)
    API->>API: Sniff magic bytes & compute SHA-256 hash
    API->>Storage: Persist sanitized file to disk
    API->>DB: INSERT Document (status=PENDING)
    API->>Redis: Enqueue Celery task (tasks.process_document)
    API-->>Frontend: HTTP 202 Accepted {id, filename, status: PENDING}

    Redis->>Worker: Consume processing task
    Worker->>DB: UPDATE Document (status=PROCESSING)
    Worker->>Redis: SET doc:{id}:progress {stage: INGESTION, percentage: 10}

    alt Digital PDF
        Worker->>Worker: PyMuPDF extract vector text & page metadata
    else Scanned PDF / Image (PNG, JPG, TIFF)
        Worker->>Worker: OpenCV deskew, denoise, Otsu binarization
        Worker->>Worker: Tesseract OCR text & per-token confidence
    else Spreadsheet (XLSX, CSV)
        Worker->>Worker: openpyxl / csv extract sheets, headers & rows
    end

    Worker->>DB: INSERT Pages (page_number, raw_text, ocr_confidence)

    alt Document / Image Text
        Worker->>LLM: extract_invoice(combined_text) [JSON Schema]
        LLM-->>Worker: Structured InvoiceExtractionSchema
        Worker->>Worker: Grounding check (verify snippets in source text)
    else Spreadsheet
        Worker->>LLM: map_spreadsheet_columns(headers)
        LLM-->>Worker: SpreadsheetColumnMapping
        Worker->>Worker: Parse rows deterministically with mapping
    end

    Worker->>DB: INSERT Extraction & LineItems

    Worker->>Worker: Deterministic Validation (math checks, tolerances)
    Worker->>DB: Check for exact/fuzzy duplicate invoices (Rapidfuzz)
    Worker->>DB: INSERT ValidationIssues (severity: ERROR/WARNING)

    Worker->>LLM: Generate text embeddings (text-embedding-004)
    Worker->>DB: INSERT Embeddings (768-dim pgvector)

    Worker->>DB: UPDATE Document (status=COMPLETED, needs_review=bool)
    Worker->>Redis: SET doc:{id}:progress {stage: COMPLETED, percentage: 100}
    Frontend->>API: Poll / SSE GET /documents/{id} & /result
    API-->>Frontend: HTTP 200 {document, extractions, validation_issues}
    Frontend-->>User: Render document viewer, extracted fields & validation badges
```

---

## 3. Hybrid Search Architecture (Reciprocal Rank Fusion)

The hybrid retrieval engine combines exact keyword matching with deep semantic vector proximity to guarantee both keyword precision and semantic recall:

```mermaid
flowchart TD
    Query["User Search Query + Structured Filters"]

    subgraph KeywordBranch ["Keyword Search (Lexical)"]
        FTS["PostgreSQL Full-Text Search"]
        TSQuery["to_tsquery('english', query)"]
        FTS -->|Rank via ts_rank_cd| KWResults["Keyword Ranked List (Rank_K)"]
    end

    subgraph SemanticBranch ["Semantic Search (Vector Proximity)"]
        GeminiEmb["Gemini text-embedding-004"]
        QueryVec["768-dimensional Dense Embedding"]
        pgvector["pgvector Cosine Distance (<=>)"]
        GeminiEmb --> QueryVec
        QueryVec --> pgvector
        pgvector --> SemResults["Semantic Ranked List (Rank_S)"]
    end

    subgraph FusionEngine ["Reciprocal Rank Fusion (RRF)"]
        RRFFormula["Score = 1/(60 + Rank_K) + 1/(60 + Rank_S)"]
        KWResults --> RRFFormula
        SemResults --> RRFFormula
    end

    subgraph FilterEngine ["Faceted Filtering Engine"]
        Filters["PostgreSQL Structured Filters:<br/>• supplier_name (ILIKE)<br/>• date_from / date_to<br/>• min_total / max_total<br/>• document status"]
        RRFFormula --> Filters
    end

    Query --> KeywordBranch
    Query --> SemanticBranch
    Filters --> RankedOutput["Final De-duplicated & Ranked Search Results"]
```

### Mathematical Formulation
The score for document $d$ across retrieval channels is computed as:
$$RRF(d) = \sum_{m \in \{K, S\}} \frac{1}{k + \text{rank}_m(d)}$$
where $k = 60$ is the standard smoothing constant dampening the outlier impact of individual high ranks.

---

## 4. Cross-Verification Reconciliation Flow

```mermaid
flowchart LR
    DocA["Primary Document (e.g., PDF Invoice)"]
    DocB["Secondary Document (e.g., Excel PO / Ledger)"]

    Match["Matcher:<br/>1. Exact Invoice Number<br/>2. Fuzzy Supplier Matching (>= 80%)"]
    DocA --> Match
    DocB --> Match

    Reconciliation["Discrepancy Evaluator:<br/>• Total Amount Match (within tolerance)<br/>• Invoice Date Consistency<br/>• Currency Consistency<br/>• Line-Item Reconciler"]
    Match --> Reconciliation

    Output["Verification Report:<br/>• is_match (boolean)<br/>• confidence (float)<br/>• discrepancies: list[DiscrepancyItem]<br/>(field, doc_a_value, doc_b_value, severity)"]
    Reconciliation --> Output
```

---

## 5. Architectural Components Breakdown

### 5.1 Storage & Magic-Byte Sniffing
Every uploaded document is inspected via `python-magic` (`libmagic`) inspecting binary signatures. Untrusted client MIME headers and file extensions are completely ignored. Supported formats:
- **PDF**: `%PDF-` magic header.
- **TIFF**: `II*\x00` (little-endian) or `MM\x00*` (big-endian).
- **PNG**: `\x89PNG\r\n\x1a\n`.
- **JPEG**: `\xff\xd8\xff`.
- **XLSX / XLS**: OpenXML ZIP container verified via `openpyxl`.
- **CSV**: Sniffed via Python standard library `csv.Sniffer`.

### 5.2 Deterministic Validation Engine
Validation is strictly deterministic Python code:
- **Missing Required Fields**: Flags `MISSING_INVOICE_NUMBER`, `MISSING_INVOICE_DATE`, `MISSING_SUPPLIER_NAME`, `MISSING_TOTAL`.
- **Arithmetic Consistency**:
  - Checks if `subtotal + tax == total` within configurable tolerance (default: $0.01).
  - Checks if $\sum \text{line\_totals} == \text{subtotal}$.
  - Checks line items: $\text{quantity} \times \text{unit\_price} == \text{line\_total}$.
- **Duplicate Detection**: Exact matching on `(invoice_number, supplier_name)` and fuzzy supplier name matching using Rapidfuzz (`token_sort_ratio >= 80`).
- **Currency Consistency**: Flags line item currencies that conflict with header currency.
- **Human Review Flagging**: Any validation error or extraction confidence $< 0.80$ flags `needs_review = true`.

### 5.3 Scalability Architecture (1,000-Page Documents)
To process massive multi-page documents (e.g., 1,000-page accounting packages) without memory exhaustion or worker timeouts:
1. **Streaming Ingestion**: Uploads stream chunked byte streams directly into shared NVMe/S3 storage.
2. **PyMuPDF Lightweight Chunking**: PyMuPDF opens PDFs in streaming read-only mode without loading all raster buffers into memory.
3. **Celery Canvas Chunking**: Pages are divided into chunks of 10-20 pages and distributed across independent Celery worker processes via Celery `group` / `chord` primitives.
4. **Redis Atomic Accumulators**: Redis atomic hashes track per-page completion percentages (`pages_done / pages_total`).
5. **Database Bulk Insertion**: Page text and embeddings are persisted using SQLAlchemy `bulk_save_objects` to avoid single-row roundtrip overhead.
