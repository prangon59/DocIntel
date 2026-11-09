"""Grounding check verifying extracted values against verbatim source document text."""

import re
from dataclasses import dataclass

from app.schemas.extraction import InvoiceExtractionSchema


@dataclass
class GroundingIssue:
    """Discrepancy where extracted value does not appear in source text."""

    field: str
    value: str
    confidence_penalty: float


def normalize_text_for_matching(text: str) -> str:
    """Normalize text for fuzzy matching by lowercasing and stripping punctuation."""
    if not text:
        return ""
    # Lowercase and replace non-alphanumeric (except decimals/hyphens) with space
    cleaned = re.sub(r"[^\w\.\-\$]", " ", text.lower())
    return " ".join(cleaned.split())


def is_grounded_in_text(value_str: str, source_text: str) -> bool:
    """Check if value string or its numeric representation appears in source text."""
    if not value_str or not str(value_str).strip():
        return True

    val_norm = normalize_text_for_matching(str(value_str))
    if not val_norm:
        return True

    source_norm = normalize_text_for_matching(source_text)

    # 1. Direct substring search
    if val_norm in source_norm:
        return True

    # 2. Strip currency symbols / commas ($1,250.00 -> 1250.00 or 1250)
    cleaned_num = re.sub(r"[^\d\.]", "", val_norm)
    if cleaned_num and (
        cleaned_num in source_norm or cleaned_num.rstrip("0").rstrip(".") in source_norm
    ):
        return True

    # 3. Token-level overlap (all tokens in value appear in source text)
    tokens = val_norm.split()
    return bool(tokens and all(t in source_norm for t in tokens))


def verify_extraction_grounding(
    extraction: InvoiceExtractionSchema,
    source_text: str,
    penalty_factor: float = 0.4,
) -> list[GroundingIssue]:
    """Verify all extracted fields against the source text.

    Penalizes confidence score for any hallucinated or ungrounded field values.

    Args:
        extraction: The parsed InvoiceExtractionSchema to verify in-place.
        source_text: Raw unparsed document text.
        penalty_factor: Multiplier to apply to confidence when ungrounded (default 0.4).

    Returns:
        List of detected GroundingIssue instances.
    """
    normalized_source = normalize_text_for_matching(source_text)
    issues: list[GroundingIssue] = []

    def _check_field(field_obj, field_name: str) -> None:
        if field_obj is None or field_obj.value is None:
            return

        val_str = str(field_obj.value)
        # Check either value or source snippet
        snippet = field_obj.source_snippet or ""
        grounded = is_grounded_in_text(val_str, normalized_source) or (
            snippet and is_grounded_in_text(snippet, normalized_source)
        )

        if not grounded:
            field_obj.is_grounded = False
            orig_conf = field_obj.confidence
            field_obj.confidence = round(max(0.0, orig_conf * penalty_factor), 3)
            issues.append(
                GroundingIssue(
                    field=field_name,
                    value=val_str,
                    confidence_penalty=round(orig_conf - field_obj.confidence, 3),
                )
            )
        else:
            field_obj.is_grounded = True

    # Check top-level fields
    _check_field(extraction.invoice_number, "invoice_number")
    _check_field(extraction.invoice_date, "invoice_date")
    _check_field(extraction.supplier_name, "supplier_name")
    _check_field(extraction.customer_name, "customer_name")
    _check_field(extraction.subtotal, "subtotal")
    _check_field(extraction.tax, "tax")
    _check_field(extraction.total, "total")
    _check_field(extraction.currency, "currency")

    # Check line items
    for i, item in enumerate(extraction.line_items):
        _check_field(item.description, f"line_item[{i}].description")
        _check_field(item.quantity, f"line_item[{i}].quantity")
        _check_field(item.unit_price, f"line_item[{i}].unit_price")
        _check_field(item.line_total, f"line_item[{i}].line_total")

    # Recompute overall confidence
    all_confs: list[float] = [
        f.confidence
        for f in (
            extraction.invoice_number,
            extraction.invoice_date,
            extraction.supplier_name,
            extraction.customer_name,
            extraction.subtotal,
            extraction.tax,
            extraction.total,
            extraction.currency,
        )
        if f is not None and f.value is not None
    ]
    if all_confs:
        extraction.overall_confidence = round(sum(all_confs) / len(all_confs), 3)

    return issues
