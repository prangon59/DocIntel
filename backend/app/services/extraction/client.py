"""Abstract LLMClient interface enabling modular swapping of LLM providers."""
from abc import ABC, abstractmethod

from app.schemas.extraction import InvoiceExtractionSchema, SpreadsheetColumnMapping


class LLMClient(ABC):
    """Abstract interface for large language model operations."""

    @abstractmethod
    async def extract_invoice(self, document_text: str) -> InvoiceExtractionSchema:
        """Extract structured invoice data from document text.

        Args:
            document_text: Raw text extracted from document pages.

        Returns:
            InvoiceExtractionSchema with per-field confidence and evidence.
        """
        pass

    @abstractmethod
    async def map_spreadsheet_columns(self, headers: list[str]) -> SpreadsheetColumnMapping:
        """Map spreadsheet column header names to standard invoice fields.

        Args:
            headers: List of detected spreadsheet header strings.

        Returns:
            SpreadsheetColumnMapping mapping columns to schema keys.
        """
        pass
