"""Structured invoice extraction Pydantic schemas with per-field evidence and Decimal money."""

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StringEvidence(BaseModel):
    """Extracted text string with confidence and verbatim source grounding snippet."""

    model_config = ConfigDict(extra="ignore")

    value: str | None = Field(default=None, description="Extracted string or null if not present")
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Extraction confidence (0-1)"
    )
    source_snippet: str | None = Field(default=None, description="Verbatim source text snippet")
    is_grounded: bool = Field(default=True, description="True if verified against source text")


class DateEvidence(BaseModel):
    """Extracted date with confidence and source grounding snippet."""

    model_config = ConfigDict(extra="ignore")

    value: str | None = Field(default=None, description="ISO 8601 date (YYYY-MM-DD) or null")
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Extraction confidence (0-1)"
    )
    source_snippet: str | None = Field(default=None, description="Verbatim source text snippet")
    is_grounded: bool = Field(default=True, description="True if verified against source text")

    def as_date(self) -> date | None:
        """Convert ISO date string to standard datetime.date."""
        if not self.value:
            return None
        try:
            return date.fromisoformat(self.value.strip())
        except Exception:
            return None


class DecimalEvidence(BaseModel):
    """Extracted financial money amount represented strictly as Decimal (never float)."""

    model_config = ConfigDict(extra="ignore")

    value: Decimal | None = Field(
        default=None, description="Extracted decimal number or null if missing"
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Extraction confidence (0-1)"
    )
    source_snippet: str | None = Field(default=None, description="Verbatim source text snippet")
    is_grounded: bool = Field(default=True, description="True if verified against source text")


class ExtractedLineItem(BaseModel):
    """Single line item extracted from an invoice."""

    model_config = ConfigDict(extra="ignore")

    description: StringEvidence = Field(default_factory=StringEvidence)
    quantity: DecimalEvidence = Field(default_factory=DecimalEvidence)
    unit_price: DecimalEvidence = Field(default_factory=DecimalEvidence)
    line_total: DecimalEvidence = Field(default_factory=DecimalEvidence)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class InvoiceLLMResponseSchema(BaseModel):
    """Structured LLM extraction schema without internal dictionary metadata."""

    model_config = ConfigDict(extra="ignore")

    invoice_number: StringEvidence | None = None
    invoice_date: DateEvidence | None = None
    supplier_name: StringEvidence | None = None
    customer_name: StringEvidence | None = None
    subtotal: DecimalEvidence | None = None
    tax: DecimalEvidence | None = None
    total: DecimalEvidence | None = None
    currency: StringEvidence | None = None
    line_items: list[ExtractedLineItem] = Field(default_factory=list)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class InvoiceExtractionSchema(InvoiceLLMResponseSchema):
    """Complete structured invoice schema according to docs/SPEC.md."""

    raw_response: dict[str, Any] | None = Field(default=None)


class SpreadsheetColumnMapping(BaseModel):
    """Mapping from spreadsheet column header names to canonical invoice schema fields."""

    model_config = ConfigDict(extra="ignore")

    invoice_number_col: str | None = None
    invoice_date_col: str | None = None
    supplier_name_col: str | None = None
    customer_name_col: str | None = None
    subtotal_col: str | None = None
    tax_col: str | None = None
    total_col: str | None = None
    currency_col: str | None = None
    item_description_col: str | None = None
    item_quantity_col: str | None = None
    item_unit_price_col: str | None = None
    item_line_total_col: str | None = None
