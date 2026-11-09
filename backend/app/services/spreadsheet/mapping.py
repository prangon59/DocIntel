"""Spreadsheet column mapping service converting tabular rows into structured invoice extractions."""
import re
from datetime import date
from decimal import Decimal
from typing import Any

from app.schemas.extraction import (
    DateEvidence,
    DecimalEvidence,
    ExtractedLineItem,
    InvoiceExtractionSchema,
    SpreadsheetColumnMapping,
    StringEvidence,
)
from app.services.spreadsheet.parser import ParsedSheet


def clean_decimal(val: Any) -> Decimal | None:
    """Parse raw cell value into Decimal."""
    if val is None:
        return None
    val_str = str(val).strip()
    # Strip currency signs and commas
    cleaned = re.sub(r"[^\d\.\-]", "", val_str)
    if not cleaned or cleaned == "-":
        return None
    try:
        return Decimal(cleaned)
    except Exception:
        return None


def clean_str(val: Any) -> str | None:
    """Clean string from cell value."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def clean_date_str(val: Any) -> str | None:
    """Format date to ISO 8601 string (YYYY-MM-DD)."""
    if val is None:
        return None
    if isinstance(val, date):
        return val.isoformat()
    val_str = str(val).strip()
    # Match common date patterns (YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY)
    iso_match = re.search(r"(\d{4})[\-/](\d{1,2})[\-/](\d{1,2})", val_str)
    if iso_match:
        y, m, d = iso_match.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    return val_str if val_str else None


def heuristic_header_mapping(headers: list[str]) -> SpreadsheetColumnMapping:
    """Heuristically map spreadsheet headers to invoice fields when LLM is unavailable."""
    mapping = SpreadsheetColumnMapping()

    for h in headers:
        norm = h.lower().strip()
        if any(kw in norm for kw in ("inv #", "invoice no", "invoice number", "invoice_no", "inv_num", "bill no")):
            mapping.invoice_number_col = h
        elif any(kw in norm for kw in ("inv date", "invoice date", "date")):
            mapping.invoice_date_col = h
        elif any(kw in norm for kw in ("supplier", "vendor", "seller")):
            mapping.supplier_name_col = h
        elif any(kw in norm for kw in ("customer", "buyer", "client")):
            mapping.customer_name_col = h
        elif any(kw in norm for kw in ("subtotal", "sub total", "net amount")):
            mapping.subtotal_col = h
        elif any(kw in norm for kw in ("tax", "vat", "gst")):
            mapping.tax_col = h
        elif any(kw in norm for kw in ("total amount", "grand total", "total", "amount")):
            if not mapping.total_col:
                mapping.total_col = h
        elif any(kw in norm for kw in ("currency", "curr")):
            mapping.currency_col = h
        elif any(kw in norm for kw in ("description", "item", "product")):
            mapping.item_description_col = h
        elif any(kw in norm for kw in ("qty", "quantity")):
            mapping.item_quantity_col = h
        elif any(kw in norm for kw in ("unit price", "price", "rate")):
            mapping.item_unit_price_col = h
        elif any(kw in norm for kw in ("line total", "item total")):
            mapping.item_line_total_col = h

    return mapping


def parse_rows_with_mapping(
    sheet: ParsedSheet,
    mapping: SpreadsheetColumnMapping | dict[str, Any],
) -> list[InvoiceExtractionSchema]:
    """Deterministically convert sheet rows into InvoiceExtractionSchema records using column mapping."""
    if isinstance(mapping, dict):
        mapping = SpreadsheetColumnMapping.model_validate(mapping)
    extractions: list[InvoiceExtractionSchema] = []

    for _r_i, row in enumerate(sheet.rows, start=1):
        # Extract invoice number
        inv_num = clean_str(row.get(mapping.invoice_number_col)) if mapping.invoice_number_col else None
        inv_date = clean_date_str(row.get(mapping.invoice_date_col)) if mapping.invoice_date_col else None
        supplier = clean_str(row.get(mapping.supplier_name_col)) if mapping.supplier_name_col else None
        customer = clean_str(row.get(mapping.customer_name_col)) if mapping.customer_name_col else None
        subtotal = clean_decimal(row.get(mapping.subtotal_col)) if mapping.subtotal_col else None
        tax = clean_decimal(row.get(mapping.tax_col)) if mapping.tax_col else None
        total = clean_decimal(row.get(mapping.total_col)) if mapping.total_col else None
        currency = clean_str(row.get(mapping.currency_col)) if mapping.currency_col else "USD"

        # Check line item columns
        item_desc = clean_str(row.get(mapping.item_description_col)) if mapping.item_description_col else None
        item_qty = clean_decimal(row.get(mapping.item_quantity_col)) if mapping.item_quantity_col else None
        item_price = clean_decimal(row.get(mapping.item_unit_price_col)) if mapping.item_unit_price_col else None
        item_total = clean_decimal(row.get(mapping.item_line_total_col)) if mapping.item_line_total_col else None

        line_items: list[ExtractedLineItem] = []
        if item_desc or item_total:
            line_items.append(
                ExtractedLineItem(
                    description=StringEvidence(
                        value=item_desc,
                        confidence=1.0 if item_desc else 0.0,
                        source_snippet=item_desc,
                    ),
                    quantity=DecimalEvidence(
                        value=item_qty,
                        confidence=1.0 if item_qty is not None else 0.0,
                        source_snippet=str(item_qty) if item_qty is not None else None,
                    ),
                    unit_price=DecimalEvidence(
                        value=item_price,
                        confidence=1.0 if item_price is not None else 0.0,
                        source_snippet=str(item_price) if item_price is not None else None,
                    ),
                    line_total=DecimalEvidence(
                        value=item_total,
                        confidence=1.0 if item_total is not None else 0.0,
                        source_snippet=str(item_total) if item_total is not None else None,
                    ),
                )
            )

        # Build schema instance
        schema = InvoiceExtractionSchema(
            invoice_number=StringEvidence(
                value=inv_num,
                confidence=1.0 if inv_num else 0.0,
                source_snippet=inv_num,
            ),
            invoice_date=DateEvidence(
                value=inv_date,
                confidence=1.0 if inv_date else 0.0,
                source_snippet=inv_date,
            ),
            supplier_name=StringEvidence(
                value=supplier,
                confidence=1.0 if supplier else 0.0,
                source_snippet=supplier,
            ),
            customer_name=StringEvidence(
                value=customer,
                confidence=1.0 if customer else 0.0,
                source_snippet=customer,
            ),
            subtotal=DecimalEvidence(
                value=subtotal,
                confidence=1.0 if subtotal is not None else 0.0,
                source_snippet=str(subtotal) if subtotal is not None else None,
            ),
            tax=DecimalEvidence(
                value=tax,
                confidence=1.0 if tax is not None else 0.0,
                source_snippet=str(tax) if tax is not None else None,
            ),
            total=DecimalEvidence(
                value=total,
                confidence=1.0 if total is not None else 0.0,
                source_snippet=str(total) if total is not None else None,
            ),
            currency=StringEvidence(
                value=currency or "USD",
                confidence=1.0 if currency else 0.0,
                source_snippet=currency,
            ),
            line_items=line_items,
            overall_confidence=1.0 if (inv_num or total) else 0.0,
        )
        extractions.append(schema)

    return extractions
