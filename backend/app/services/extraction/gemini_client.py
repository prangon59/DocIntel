"""Google Gemini implementation of the LLMClient interface using the Google GenAI SDK.

Includes:
- Robust rate limiting honoring free-tier limits (RPM and concurrency bounds)
- Exponential backoff with random jitter and Retry-After hint extraction for HTTP 429 / quota errors
- Disk response caching keyed by SHA-256 prompt hash to prevent redundant quota usage
"""

import asyncio
import hashlib
import json
import logging
import random
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.extraction import (
    InvoiceExtractionSchema,
    InvoiceLLMResponseSchema,
    SpreadsheetColumnMapping,
)
from app.services.extraction.client import LLMClient
from app.services.extraction.rate_limiter import (
    extract_retry_after,
    get_llm_rate_limiter,
    is_rate_limit_or_quota_error,
)

logger = logging.getLogger("docintel.llm.gemini")

INVOICE_EXTRACTION_SYSTEM_INSTRUCTION = """You are an expert document intelligence AI specializing in business invoice data extraction.
Extract structured invoice information from the provided document text.

CRITICAL RULES:
1. NEVER invent, hallucinate, or estimate values.
2. If a field (e.g., invoice_number, invoice_date, customer_name, tax, subtotal) is not explicitly present in the document text, set its value to null and confidence to 0.0.
3. Every non-null value MUST include a source_snippet containing the exact verbatim text snippet where the value appears.
4. All money amounts must be exact numeric values in Decimal format without currency symbols.
5. All dates must follow the ISO 8601 format (YYYY-MM-DD). If day or month is unclear, format as best standard or set to null if invalid.
6. The currency field must be an ISO 4217 code (e.g., USD, EUR, GBP, CAD).
7. Extract all line items individually with description, quantity, unit_price, and line_total.
"""

SPREADSHEET_MAPPING_SYSTEM_INSTRUCTION = """You are an expert financial data mapper.
Given a list of spreadsheet column header names, map each standard invoice field to the exact column name from the list that represents it.
If no column in the list matches a field, set that field to null.
Do not invent column names that are not in the input list.
"""


class GeminiLLMClient(LLMClient):
    """Google Gemini LLMClient leveraging the official Google GenAI SDK with rate-limiting and caching."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int = 5,
        cache_dir: str | Path | None = None,
        bypass_cache: bool = False,
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.LLM_MODEL or settings.GEMINI_MODEL
        self.timeout_seconds = timeout_seconds or settings.LLM_TIMEOUT_SECONDS
        self.max_retries = max_retries
        self.rate_limiter = get_llm_rate_limiter()
        self.bypass_cache = bypass_cache
        self.total_rate_limit_wait: float = 0.0

        raw_cache_dir = cache_dir
        self.cache_dir: Path | None = Path(raw_cache_dir) if raw_cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        """Lazily initialize genai.Client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not configured.")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _get_cache_key(self, instruction: str, prompt: str) -> str:
        """Compute deterministic SHA-256 cache key for prompt and model."""
        content = f"{self.model_name}:{instruction}:{prompt}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _read_from_cache(self, cache_key: str) -> dict[str, Any] | None:
        """Read cached response if caching is active and file exists."""
        if self.bypass_cache or not self.cache_dir:
            return None
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    data = json.load(f)
                logger.info("LLM cache hit: %s", cache_key[:12])
                return data
            except Exception as e:
                logger.warning("Failed reading LLM cache %s: %s", cache_file, e)
        return None

    def _write_to_cache(self, cache_key: str, data: dict[str, Any]) -> None:
        """Write response to disk cache."""
        if not self.cache_dir:
            return
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.warning("Failed writing to LLM cache %s: %s", cache_file, e)

    async def extract_invoice(self, document_text: str) -> InvoiceExtractionSchema:
        """Extract structured invoice fields with structured JSON schema, rate limiting, and backoff."""
        prompt = f'Document Text:\n"""\n{document_text}\n"""'
        cache_key = self._get_cache_key(INVOICE_EXTRACTION_SYSTEM_INSTRUCTION, prompt)

        cached_data = self._read_from_cache(cache_key)
        if cached_data is not None:
            parsed = InvoiceExtractionSchema.model_validate(cached_data)
            parsed.raw_response = cached_data
            return parsed

        client = self._get_client()

        config = types.GenerateContentConfig(
            system_instruction=INVOICE_EXTRACTION_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=InvoiceLLMResponseSchema,
            temperature=0.0,
        )

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                # Wait for rate limit slot
                async with self.rate_limiter.acquire() as wait_sec:
                    self.total_rate_limit_wait += wait_sec

                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.models.generate_content,
                        model=self.model_name,
                        contents=prompt,
                        config=config,
                    ),
                    timeout=self.timeout_seconds,
                )

                if not response.text:
                    raise ValueError("Received empty response from Gemini API.")

                data = json.loads(response.text)
                parsed = InvoiceExtractionSchema.model_validate(data)
                parsed.raw_response = data

                self._write_to_cache(cache_key, data)
                return parsed

            except (json.JSONDecodeError, ValueError) as val_err:
                logger.warning("Attempt %d/%d: Invalid format: %s", attempt, self.max_retries, val_err)
                last_error = val_err
                if attempt < self.max_retries:
                    delay = (2.0 * (2 ** (attempt - 1))) + random.uniform(0.2, 1.0)
                    await asyncio.sleep(delay)

            except Exception as exc:
                last_error = exc
                if is_rate_limit_or_quota_error(exc):
                    retry_after = extract_retry_after(exc)
                    base_delay = 4.0 * (2 ** (attempt - 1))
                    jitter = random.uniform(0.5, 2.0)
                    delay = base_delay + jitter
                    if retry_after is not None:
                        delay = max(delay, retry_after + random.uniform(0.5, 1.5))

                    self.total_rate_limit_wait += delay
                    logger.warning(
                        "Attempt %d/%d: Gemini 429/Quota hit; backing off %.1fs (retry-after=%s)",
                        attempt,
                        self.max_retries,
                        delay,
                        retry_after,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.warning("Attempt %d/%d: Gemini API request failed: %s", attempt, self.max_retries, exc)
                    if attempt < self.max_retries:
                        delay = (2.0 * (2 ** (attempt - 1))) + random.uniform(0.2, 1.0)
                        await asyncio.sleep(delay)

        raise RuntimeError(
            f"Gemini invoice extraction failed after {self.max_retries} attempts: {last_error}"
        )

    async def map_spreadsheet_columns(self, headers: list[str]) -> SpreadsheetColumnMapping:
        """Map spreadsheet headers to invoice schema with rate limiting and backoff."""
        headers_json = json.dumps(headers)
        prompt = f"Spreadsheet Headers:\n{headers_json}"
        cache_key = self._get_cache_key(SPREADSHEET_MAPPING_SYSTEM_INSTRUCTION, prompt)

        cached_data = self._read_from_cache(cache_key)
        if cached_data is not None:
            return SpreadsheetColumnMapping.model_validate(cached_data)

        client = self._get_client()

        config = types.GenerateContentConfig(
            system_instruction=SPREADSHEET_MAPPING_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=SpreadsheetColumnMapping,
            temperature=0.0,
        )

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with self.rate_limiter.acquire() as wait_sec:
                    self.total_rate_limit_wait += wait_sec

                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.models.generate_content,
                        model=self.model_name,
                        contents=prompt,
                        config=config,
                    ),
                    timeout=self.timeout_seconds,
                )

                if not response.text:
                    return SpreadsheetColumnMapping()

                data = json.loads(response.text)
                mapping = SpreadsheetColumnMapping.model_validate(data)
                self._write_to_cache(cache_key, data)
                return mapping

            except Exception as exc:
                last_error = exc
                if is_rate_limit_or_quota_error(exc):
                    retry_after = extract_retry_after(exc)
                    delay = (4.0 * (2 ** (attempt - 1))) + random.uniform(0.5, 2.0)
                    if retry_after is not None:
                        delay = max(delay, retry_after + random.uniform(0.5, 1.5))
                    self.total_rate_limit_wait += delay
                    logger.warning(
                        "Attempt %d/%d (mapping): Gemini 429 hit; backing off %.1fs",
                        attempt,
                        self.max_retries,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.warning("Attempt %d/%d (mapping): API call failed: %s", attempt, self.max_retries, exc)
                    if attempt < self.max_retries:
                        await asyncio.sleep(2.0 * attempt)

        logger.warning("LLM column mapping failed after %d attempts (%s); falling back to heuristics.", self.max_retries, last_error)
        from app.services.spreadsheet.mapping import heuristic_header_mapping
        return heuristic_header_mapping(headers)
