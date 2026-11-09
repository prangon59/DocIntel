# System Architecture: AI Document Intelligence

## Overview

The system is organized as a decoupled, microservices-ready monorepo comprising:
- **FastAPI Backend (`/backend`)**: High-throughput asynchronous REST API providing file ingestion, document query, result retrieval, manual correction, and search.
- **PostgreSQL 16 + pgvector**: Unified relational metadata store, full-text inverted index (`tsvector`), and high-dimensional vector embeddings for semantic search.
- **Redis 7**: Distributed task queue broker and in-memory cache for ingestion state and live progress counters.
- **Celery Distributed Workers**: Asynchronous, parallel background workers responsible for PDF chunking, OpenCV image preprocessing, Tesseract OCR fallback, spreadsheet parsing, LLM structured extraction, and deterministic validation.
- **Next.js Web Frontend (`/frontend`)**: Modern React interface providing multi-file drag-and-drop ingestion, live page-level progress monitoring, side-by-side inspection with original document rendering, inline validation alerts, editable fields, and hybrid search.

## High-Level Architecture Diagram

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
        Excel["pandas + openpyxl (Spreadsheets)"]
        Worker1 --> PyMuPDF
        Worker1 --> OCR
        Worker2 --> Excel
    end

    subgraph IntelligenceLayer ["Intelligence & Validation Engine"]
        LLM["Gemini 2.5 Flash (via LLMClient)"]
        Validator["Deterministic Validation Engine"]
        CrossVerifier["Cross-Verification Service"]
        Embedder["Vector Embedder"]

        Worker1 & Worker2 -->|Extract Structured Data| LLM
        Worker1 & Worker2 -->|Verify Math & Deduplicate| Validator
        Worker1 & Worker2 -->|Cross Check Docs| CrossVerifier
        Worker1 & Worker2 -->|Generate Vectors| Embedder
    end

    IntelligenceLayer -->|Persist Extractions, Issues, Embeddings| Postgres
```

## Detailed Processing Flow

1. **Ingestion & Validation**:
   - Client uploads document (PDF, PNG, JPG, TIFF, XLSX, XLS, CSV).
   - FastAPI sniffs file magic bytes to verify genuine file type, computes SHA-256 hash to detect duplicate files.
   - Saves file to disk/volume, inserts a `Document` record with status `PENDING`, and immediately returns job IDs (HTTP 202).
2. **Task Dispatching & Parallel Chunking**:
   - For multi-page PDFs, PyMuPDF identifies page count.
   - Tasks are split into parallel Celery subtasks per page or chunk.
   - Redis keeps aggregate atomic counters (`pages_done`, `pages_total`).
3. **Text Extraction & OCR Fallback**:
   - Digital text is extracted per page. If characters `< 30`, OCR fallback activates:
   - OpenCV executes deskew, denoise, and Otsu adaptive thresholding.
   - Tesseract extracts text and per-token confidence.
4. **LLM Extraction & Grounding**:
   - Aggregated page text is sent to Gemini 2.5 Flash via `LLMClient` with strict Pydantic JSON schema.
   - Extracted values are deterministically checked against raw text (grounding verification).
   - Missing fields are strictly recorded as `null` with `0.0` confidence (no hallucinated values).
5. **Deterministic Validation & Deduplication**:
   - Pure Python validation rules verify line-item math (`sum(line_totals) == subtotal`, `subtotal + tax == total`).
   - Duplicate detection checks exact and fuzzy matches (`rapidfuzz`) against existing invoices.
   - Records with errors or low confidence are flagged `needs_review = true`.
6. **Cross-Verification & Indexing**:
   - Matching invoices across document pairs (PDF-PDF or PDF-Excel) are verified for numerical discrepancies.
   - Full text is indexed in PostgreSQL `tsvector` and chunk embeddings are indexed in `pgvector`.
