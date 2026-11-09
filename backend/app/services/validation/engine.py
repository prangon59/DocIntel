"""Deterministic financial validation engine.

Evaluates missing fields, mathematical calculations, currency consistency,
and sets needs_review flag. Contains zero LLM logic.
"""
from dataclasses import dataclass
from decimal import Decimal

from app.core.config import settings
from app.models.validation import IssueSeverity
from app.schemas.extraction import InvoiceExtractionSchema
from app.services.extraction.grounding import GroundingIssue
from app.services.validation.duplicates import ValidationIssueData


@dataclass
class ValidationReport:
    """Consolidated validation report with issues and review flag."""

    issues: list[ValidationIssueData]
    needs_review: bool
    is_valid: bool


def validate_extracted_invoice(
    extraction: InvoiceExtractionSchema,
    tolerance: Decimal | None = None,
    grounding_issues: list[GroundingIssue] | None = None,
) -> ValidationReport:
    """Execute deterministic validation checks on an extracted invoice.

    Args:
        extraction: Parsed invoice extraction schema.
        tolerance: Configurable math tolerance (default settings.MATH_TOLERANCE).
        grounding_issues: List of detected grounding anomalies from source verification.

    Returns:
        ValidationReport containing all identified issues and needs_review decision.
    """
    tol = tolerance if tolerance is not None else settings.MATH_TOLERANCE
    issues: list[ValidationIssueData] = []

    # 1. Missing Required Fields
    if not extraction.invoice_number or not extraction.invoice_number.value:
        issues.append(
            ValidationIssueData(
                code="MISSING_INVOICE_NUMBER",
                severity=IssueSeverity.ERROR,
                field="invoice_number",
                message="Invoice number is missing or empty.",
            )
        )

    if not extraction.supplier_name or not extraction.supplier_name.value:
        issues.append(
            ValidationIssueData(
                code="MISSING_SUPPLIER_NAME",
                severity=IssueSeverity.ERROR,
                field="supplier_name",
                message="Supplier / vendor name is missing.",
            )
        )

    if not extraction.invoice_date or not extraction.invoice_date.value:
        issues.append(
            ValidationIssueData(
                code="MISSING_INVOICE_DATE",
                severity=IssueSeverity.ERROR,
                field="invoice_date",
                message="Invoice date is missing.",
            )
        )

    if not extraction.total or extraction.total.value is None:
        issues.append(
            ValidationIssueData(
                code="MISSING_TOTAL",
                severity=IssueSeverity.ERROR,
                field="total",
                message="Invoice grand total amount is missing.",
            )
        )

    # 2. Negative Amount Checks
    for field_name, dec_evidence in [
        ("subtotal", extraction.subtotal),
        ("tax", extraction.tax),
        ("total", extraction.total),
    ]:
        if dec_evidence and dec_evidence.value is not None and dec_evidence.value < Decimal("0.00"):
            issues.append(
                ValidationIssueData(
                    code="NEGATIVE_AMOUNT",
                    severity=IssueSeverity.ERROR,
                    field=field_name,
                    message=f"{field_name.capitalize()} cannot be negative: {dec_evidence.value}",
                    details={"field": field_name, "value": str(dec_evidence.value)},
                )
            )

    # 3. Mathematical Consistency Checks
    subtotal = extraction.subtotal.value if extraction.subtotal else None
    tax = extraction.tax.value if extraction.tax else None
    total = extraction.total.value if extraction.total else None

    # Check: subtotal + tax ~= total
    if subtotal is not None and total is not None:
        effective_tax = tax if tax is not None else Decimal("0.00")
        expected_total = subtotal + effective_tax
        diff = abs(expected_total - total)
        if diff > tol:
            issues.append(
                ValidationIssueData(
                    code="MATH_MISMATCH_TOTAL",
                    severity=IssueSeverity.ERROR,
                    field="total",
                    message=(
                        f"Mathematical inconsistency: Subtotal ({subtotal}) + Tax ({effective_tax}) = "
                        f"{expected_total}, which does not match Grand Total ({total}). Diff: {diff}"
                    ),
                    details={
                        "subtotal": str(subtotal),
                        "tax": str(effective_tax),
                        "expected_total": str(expected_total),
                        "actual_total": str(total),
                        "difference": str(diff),
                        "tolerance": str(tol),
                    },
                )
            )

    # Check: sum(line_totals) ~= subtotal
    if extraction.line_items and subtotal is not None:
        items_with_total = [
            item.line_total.value
            for item in extraction.line_items
            if item.line_total.value is not None
        ]
        if items_with_total:
            sum_lines = sum(items_with_total)
            line_diff = abs(sum_lines - subtotal)
            if line_diff > tol:
                issues.append(
                    ValidationIssueData(
                        code="MATH_MISMATCH_SUBTOTAL",
                        severity=IssueSeverity.ERROR,
                        field="subtotal",
                        message=(
                            f"Sum of line item totals ({sum_lines}) does not match invoice subtotal ({subtotal}). "
                            f"Diff: {line_diff}"
                        ),
                        details={
                            "sum_line_totals": str(sum_lines),
                            "subtotal": str(subtotal),
                            "difference": str(line_diff),
                            "tolerance": str(tol),
                        },
                    )
                )

    # Check line item arithmetic: quantity * unit_price ~= line_total
    for idx, item in enumerate(extraction.line_items, start=1):
        q = item.quantity.value
        p = item.unit_price.value
        lt = item.line_total.value
        if q is not None and p is not None and lt is not None:
            expected_lt = round(q * p, 2)
            item_diff = abs(expected_lt - lt)
            if item_diff > tol:
                issues.append(
                    ValidationIssueData(
                        code="MATH_MISMATCH_LINE_ITEM",
                        severity=IssueSeverity.WARNING,
                        field=f"line_items[{idx}].line_total",
                        message=(
                            f"Line item {idx} ({item.description.value or 'item'}): "
                            f"Quantity ({q}) * Unit Price ({p}) = {expected_lt}, but line total is {lt}."
                        ),
                        details={
                            "item_index": idx,
                            "quantity": str(q),
                            "unit_price": str(p),
                            "expected_total": str(expected_lt),
                            "actual_total": str(lt),
                            "difference": str(item_diff),
                        },
                    )
                )

    # 4. Currency Consistency Check
    curr = extraction.currency.value if extraction.currency else None
    if curr:
        curr_clean = curr.strip().upper()
        if len(curr_clean) != 3 or not curr_clean.isalpha():
            issues.append(
                ValidationIssueData(
                    code="INVALID_CURRENCY",
                    severity=IssueSeverity.WARNING,
                    field="currency",
                    message=f"Currency '{curr}' is not a valid 3-letter ISO 4217 currency code.",
                )
            )

    # 5. Low Confidence Check
    if extraction.overall_confidence < settings.CONFIDENCE_THRESHOLD:
        issues.append(
            ValidationIssueData(
                code="LOW_CONFIDENCE",
                severity=IssueSeverity.WARNING,
                field="general",
                message=(
                    f"Overall extraction confidence ({extraction.overall_confidence:.2f}) is below "
                    f"the required threshold ({settings.CONFIDENCE_THRESHOLD:.2f})."
                ),
                details={
                    "confidence": extraction.overall_confidence,
                    "threshold": settings.CONFIDENCE_THRESHOLD,
                },
            )
        )

    # 6. Include Grounding Issues
    if grounding_issues:
        for gi in grounding_issues:
            issues.append(
                ValidationIssueData(
                    code="UNGROUNDED_VALUE",
                    severity=IssueSeverity.WARNING,
                    field=gi.field,
                    message=f"Extracted value '{gi.value}' was not grounded in the source document text.",
                    details={"field": gi.field, "value": gi.value, "penalty": gi.confidence_penalty},
                )
            )

    # Decision on needs_review
    has_errors = any(issue.severity == IssueSeverity.ERROR for issue in issues)
    needs_review = has_errors or extraction.overall_confidence < settings.CONFIDENCE_THRESHOLD

    return ValidationReport(
        issues=issues,
        needs_review=needs_review,
        is_valid=not has_errors,
    )
