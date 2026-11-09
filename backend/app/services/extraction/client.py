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


class MockLLMClient(LLMClient):
    """Deterministic mock LLMClient for testing without external API calls."""

    async def extract_invoice(self, document_text: str) -> InvoiceExtractionSchema:
        from decimal import Decimal

        from app.schemas.extraction import (
            DateEvidence,
            DecimalEvidence,
            ExtractedLineItem,
            StringEvidence,
        )

        return InvoiceExtractionSchema(
            invoice_number=StringEvidence(
                value="INV-2024-001",
                confidence=0.95,
                source_snippet="INV-2024-001" if "INV-2024-001" in document_text else None,
            ),
            supplier_name=StringEvidence(
                value="Acme Industrial Supplies Ltd",
                confidence=0.92,
                source_snippet="Acme" if "Acme" in document_text else None,
            ),
            invoice_date=DateEvidence(value="2024-05-15", confidence=0.90, source_snippet="2024-05-15"),
            subtotal=DecimalEvidence(value=Decimal("500.00"), confidence=0.95, source_snippet="500.00"),
            tax=DecimalEvidence(value=Decimal("50.00"), confidence=0.90, source_snippet="50.00"),
            total=DecimalEvidence(value=Decimal("550.00"), confidence=0.98, source_snippet="550.00"),
            currency=StringEvidence(value="USD", confidence=0.99, source_snippet="USD"),
            line_items=[
                ExtractedLineItem(
                    description=StringEvidence(value="Widget A", confidence=0.90),
                    quantity=DecimalEvidence(value=Decimal("10.00"), confidence=0.90),
                    unit_price=DecimalEvidence(value=Decimal("25.00"), confidence=0.90),
                    line_total=DecimalEvidence(value=Decimal("250.00"), confidence=0.95),
                ),
                ExtractedLineItem(
                    description=StringEvidence(value="Gadget B", confidence=0.90),
                    quantity=DecimalEvidence(value=Decimal("2.00"), confidence=0.90),
                    unit_price=DecimalEvidence(value=Decimal("125.00"), confidence=0.90),
                    line_total=DecimalEvidence(value=Decimal("250.00"), confidence=0.95),
                ),
            ],
            overall_confidence=0.95,
        )

    async def map_spreadsheet_columns(self, headers: list[str]) -> SpreadsheetColumnMapping:
        mapping: dict[str, str] = {}
        for h in headers:
            hl = h.lower()
            if "invoice" in hl and ("num" in hl or "no" in hl or "id" in hl):
                mapping["invoice_number"] = h
            elif "vendor" in hl or "supplier" in hl:
                mapping["supplier_name"] = h
            elif "customer" in hl or "client" in hl:
                mapping["customer_name"] = h
            elif "date" in hl and "due" not in hl:
                mapping["invoice_date"] = h
            elif "due" in hl:
                mapping["due_date"] = h
            elif "subtotal" in hl or "sub" in hl:
                mapping["subtotal"] = h
            elif "tax" in hl or "vat" in hl:
                mapping["tax"] = h
            elif "total" in hl or "amount" in hl:
                mapping["total"] = h
            elif "currency" in hl:
                mapping["currency"] = h
        return SpreadsheetColumnMapping(column_mapping=mapping, confidence=0.95)

