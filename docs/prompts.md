# Prompts

## Development Prompts (Agentic AI Workflow)

### Turn 1: Project Initialization & Phase 0
```
Read docs/task-brief.pdf (the original assignment) and docs/SPEC.md fully,
and follow the workspace rules. If the two ever conflict, the task brief wins
and you must tell me. Start Phase 0 only: implementation plan artifact,
repo skeleton, and docker-compose. Wait for my approval before Phase 1.
```

### Turn 2: Phase 1 Approval & Ingestion Pipeline
```
Plan approved. Proceed with Phase 1 only. Before you start, confirm that:
- the Postgres image includes pgvector,
- the backend Dockerfile installs tesseract-ocr (with English language data),
- all file handling uses magic-byte detection.

Add a small set of test fixtures: a digital PDF, a scanned image, a multi-sheet
XLSX, a CSV and a corrupted file. Do not start Phase 2. When finished, run the
tests and give me a summary artifact.
```

### Turn 3: Phase 2 Approval, AI Extraction & Validation
```
Phase 1 approved. Re-read docs/SPEC.md and the rules, then implement Phase 2 only.
Plan first, then build:
- LLMClient interface with a Gemini implementation (structured JSON output,
  timeouts, retries on invalid JSON). Check the current Gemini model name and
  SDK in the official docs before using them.
- Pydantic extraction schema with Decimal money, null for missing values,
  per-field confidence and source_snippet.
- Grounding check against the source text.
- Spreadsheet column mapping (LLM-assisted header mapping, then deterministic parsing).
- Deterministic validation engine: missing fields, math checks, tolerance
  config, duplicate detection (exact and fuzzy), currency consistency,
  needs_review logic.
- Wire extraction and validation into the Celery pipeline after text extraction.
- Tests with a mocked LLM, plus one optional live-LLM smoke test that is
  skipped when no API key is set.
- Save every prompt in docs/prompts.md.
Do not start Phase 3. Run tests and give me a summary artifact.
```

---

## Product Prompts (AI Extraction Engine)

### 1. Invoice Extraction Prompt

* **Target Model**: `gemini-2.5-flash` (via Google GenAI SDK `google-genai` with `response_schema=InvoiceExtractionSchema`)
* **Temperature**: `0.0` (deterministic output)
* **Response Format**: `application/json` (Pydantic validated)

#### System Instruction:
```text
You are an expert document intelligence AI specializing in business invoice data extraction.
Extract structured invoice information from the provided document text.

CRITICAL RULES:
1. NEVER invent, hallucinate, or estimate values.
2. If a field (e.g., invoice_number, invoice_date, customer_name, tax, subtotal) is not explicitly present in the document text, set its value to null and confidence to 0.0.
3. Every non-null value MUST include a source_snippet containing the exact verbatim text snippet where the value appears.
4. All money amounts must be exact numeric values in Decimal format without currency symbols.
5. All dates must follow the ISO 8601 format (YYYY-MM-DD). If day or month is unclear, format as best standard or set to null if invalid.
6. The currency field must be an ISO 4217 code (e.g., USD, EUR, GBP, CAD).
7. Extract all line items individually with description, quantity, unit_price, and line_total.
```

#### User Prompt:
```text
Document Text:
"""
{document_text}
"""
```

---

### 2. Spreadsheet Column Mapping Prompt

* **Target Model**: `gemini-2.5-flash` (via Google GenAI SDK with `response_schema=SpreadsheetColumnMapping`)
* **Temperature**: `0.0`
* **Response Format**: `application/json`

#### System Instruction:
```text
You are an expert financial data mapper.
Given a list of spreadsheet column header names, map each standard invoice field to the exact column name from the list that represents it.
If no column in the list matches a field, set that field to null.
Do not invent column names that are not in the input list.
```

#### User Prompt:
```text
Spreadsheet Headers:
{headers_json}
```
