"""Google Gemini implementation of the LLMClient interface using the Google GenAI SDK."""
import asyncio
import json
import logging

from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.extraction import InvoiceExtractionSchema, SpreadsheetColumnMapping
from app.services.extraction.client import LLMClient

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
    """Google Gemini LLMClient leveraging the official Google GenAI SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self.timeout_seconds = timeout_seconds or settings.LLM_TIMEOUT_SECONDS
        self.max_retries = max_retries
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        """Lazily initialize genai.Client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not configured.")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def extract_invoice(self, document_text: str) -> InvoiceExtractionSchema:
        """Extract structured invoice fields with structured JSON schema and exponential backoff retries."""
        client = self._get_client()

        config = types.GenerateContentConfig(
            system_instruction=INVOICE_EXTRACTION_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=InvoiceExtractionSchema,
            temperature=0.0,
        )

        prompt = f"Document Text:\n\"\"\"\n{document_text}\n\"\"\""

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                # Wrap synchronous SDK call in asyncio.to_thread with timeout
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

                # Parse and validate into Pydantic schema
                data = json.loads(response.text)
                parsed = InvoiceExtractionSchema.model_validate(data)
                parsed.raw_response = data
                return parsed

            except (json.JSONDecodeError, ValueError) as val_err:
                logger.warning("Attempt %d: Invalid JSON / extraction format: %s", attempt, val_err)
                last_error = val_err
                if attempt < self.max_retries:
                    await asyncio.sleep(2**attempt)
            except Exception as exc:
                logger.warning("Attempt %d: Gemini API request failed: %s", attempt, exc)
                last_error = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(2**attempt)

        raise RuntimeError(f"Gemini invoice extraction failed after {self.max_retries} attempts: {last_error}")

    async def map_spreadsheet_columns(self, headers: list[str]) -> SpreadsheetColumnMapping:
        """Map spreadsheet headers to invoice schema using structured JSON."""
        client = self._get_client()

        config = types.GenerateContentConfig(
            system_instruction=SPREADSHEET_MAPPING_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=SpreadsheetColumnMapping,
            temperature=0.0,
        )

        headers_json = json.dumps(headers)
        prompt = f"Spreadsheet Headers:\n{headers_json}"

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
        return SpreadsheetColumnMapping.model_validate(data)
