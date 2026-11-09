"""Unit tests for Phase 2 extraction schemas, grounding checks, and LLM client."""

import os
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.schemas.extraction import (
    DecimalEvidence,
    ExtractedLineItem,
    InvoiceExtractionSchema,
    StringEvidence,
)
from app.services.extraction.gemini_client import GeminiLLMClient
from app.services.extraction.grounding import (
    is_grounded_in_text,
    normalize_text_for_matching,
    verify_extraction_grounding,
)


def test_schema_valid_and_null_missing_fields():
    """Missing fields must default to None rather than being fabricated."""
    data = {
        "invoice_number": {"value": "INV-100", "confidence": 0.95, "source_snippet": "INV-100"},
        "supplier_name": {"value": "Acme Corp", "confidence": 0.90, "source_snippet": "Acme Corp"},
        "total": {"value": Decimal("100.50"), "confidence": 0.99, "source_snippet": "$100.50"},
    }
    extracted = InvoiceExtractionSchema(**data)
    assert extracted.invoice_number is not None
    assert extracted.invoice_number.value == "INV-100"
    assert extracted.total is not None
    assert extracted.total.value == Decimal("100.50")
    # Missing fields are truly None
    assert extracted.customer_name is None
    assert extracted.invoice_date is None
    assert extracted.due_date is None if hasattr(extracted, "due_date") else True
    assert extracted.subtotal is None
    assert extracted.tax is None
    assert extracted.line_items == []


def test_schema_money_is_decimal():
    """Verify that money fields preserve exact Decimal precision."""
    item = ExtractedLineItem(
        description=StringEvidence(value="Widget A", confidence=0.9),
        quantity=DecimalEvidence(value=Decimal("3.00"), confidence=0.9),
        unit_price=DecimalEvidence(value=Decimal("12.33"), confidence=0.9),
        line_total=DecimalEvidence(value=Decimal("36.99"), confidence=0.9),
    )
    assert isinstance(item.line_total.value, Decimal)
    assert item.line_total.value == Decimal("36.99")


def test_grounding_normalization():
    assert normalize_text_for_matching("Total:  $1,234.56 USD\n") == "total $1 234.56 usd"
    assert normalize_text_for_matching("Invoice\u00a0#123") == "invoice 123"


def test_is_grounded_in_text():
    raw_text = "Acme Supplies Inc.\nInvoice: INV-9901\nDate: 2024-03-15\nTotal: $1,500.00"
    assert is_grounded_in_text("INV-9901", raw_text) is True
    assert is_grounded_in_text("Acme Supplies", raw_text) is True
    assert is_grounded_in_text("2024-03-15", raw_text) is True
    assert is_grounded_in_text("$1,500.00", raw_text) is True
    # Non-existent or hallucinated text
    assert is_grounded_in_text("Global Logistics Corp", raw_text) is False
    assert is_grounded_in_text("999-NONEXISTENT", raw_text) is False


def test_verify_extraction_grounding_penalizes_hallucinations():
    raw_text = "Acme Supplies Inc.\nInvoice: INV-9901\nTotal: $500.00"
    extraction = InvoiceExtractionSchema(
        invoice_number=StringEvidence(value="INV-9901", confidence=0.95, source_snippet="INV-9901"),
        supplier_name=StringEvidence(
            value="Acme Supplies Inc.", confidence=0.95, source_snippet="Acme Supplies Inc."
        ),
        customer_name=StringEvidence(
            value="Hallucinated Corp",
            confidence=0.90,
            source_snippet="Hallucinated Corp",
        ),
        total=DecimalEvidence(value=Decimal("500.00"), confidence=0.98, source_snippet="$500.00"),
    )

    issues = verify_extraction_grounding(extraction, raw_text)
    assert len(issues) == 1
    assert issues[0].field == "customer_name"
    # Confidence was penalized
    assert extraction.customer_name is not None
    assert extraction.customer_name.confidence <= 0.45
    # Grounded fields retained confidence
    assert extraction.invoice_number is not None and extraction.invoice_number.confidence == 0.95
    assert extraction.supplier_name is not None and extraction.supplier_name.confidence == 0.95


@pytest.mark.asyncio
async def test_gemini_client_mock_structured_extraction():
    """Verify GeminiLLMClient parses JSON and returns typed schema."""
    fake_json = """{
        "invoice_number": {"value": "INV-777", "confidence": 0.95, "source_snippet": "INV-777"},
        "supplier_name": {"value": "Tech Corp", "confidence": 0.92, "source_snippet": "Tech Corp"},
        "total": {"value": "120.00", "confidence": 0.98, "source_snippet": "$120.00"},
        "subtotal": {"value": "100.00", "confidence": 0.98, "source_snippet": "$100.00"},
        "tax": {"value": "20.00", "confidence": 0.98, "source_snippet": "$20.00"},
        "currency": {"value": "USD", "confidence": 0.99, "source_snippet": "$"},
        "line_items": []
    }"""

    client = GeminiLLMClient(api_key="fake-test-key")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = fake_json
    mock_client.models.generate_content.return_value = mock_response
    client._client = mock_client

    result = await client.extract_invoice("Invoice INV-777 Tech Corp Total: $120.00")

    assert isinstance(result, InvoiceExtractionSchema)
    assert result.invoice_number is not None and result.invoice_number.value == "INV-777"
    assert result.total is not None and result.total.value == Decimal("120.00")
    assert result.tax is not None and result.tax.value == Decimal("20.00")


@pytest.mark.asyncio
async def test_gemini_client_retries_on_invalid_json():
    """Verify GeminiLLMClient retries when LLM returns invalid JSON."""
    client = GeminiLLMClient(api_key="fake-test-key")

    bad_response = MagicMock()
    bad_response.text = "This is not valid JSON at all {"

    good_response = MagicMock()
    good_response.text = """{
        "invoice_number": {"value": "INV-RETRY", "confidence": 0.95, "source_snippet": "INV-RETRY"}
    }"""

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [bad_response, good_response]
    client._client = mock_client

    result = await client.extract_invoice("Some invoice text")

    assert mock_client.models.generate_content.call_count == 2
    assert result.invoice_number is not None and result.invoice_number.value == "INV-RETRY"


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"), reason="Live Gemini test skipped (no GEMINI_API_KEY set)"
)
async def test_gemini_live_smoke():
    """Optional live Gemini smoke test verifying actual SDK call when API key is provided."""
    client = GeminiLLMClient()
    sample_text = """
    INVOICE #INV-LIVE-001
    Supplier: Apex Solutions LLC
    Date: 2025-01-10
    Item 1: Software License, Qty: 1, Price: $500.00, Total: $500.00
    Subtotal: $500.00
    Tax: $50.00
    Total: $550.00
    """
    result = await client.extract_invoice(sample_text)
    assert result.invoice_number is not None
    assert result.invoice_number.value is not None
    assert "INV-LIVE" in result.invoice_number.value
    assert result.total is not None
    assert result.total.value == Decimal("550.00")
