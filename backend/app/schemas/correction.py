"""Correction schemas for manual reviewer overrides and audit history."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LineItemCorrection(BaseModel):
    """Line item correction entry."""

    model_config = ConfigDict(extra="ignore")

    id: UUID | None = None
    description: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    line_total: Decimal | None = None


class CorrectionPayload(BaseModel):
    """Payload for manual review corrections."""

    model_config = ConfigDict(extra="ignore")

    invoice_number: str | None = None
    invoice_date: date | None = None
    supplier_name: str | None = None
    customer_name: str | None = None
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    total: Decimal | None = None
    currency: str | None = None
    line_items: list[LineItemCorrection] | None = None
    reason: str | None = Field(
        default="Manual review adjustment", description="Audit reason for changes"
    )
    updated_by: str = Field(
        default="reviewer", description="User identifier who performed correction"
    )


class CorrectionAuditItem(BaseModel):
    """Audit record entry for human edits."""

    model_config = ConfigDict(extra="ignore")

    id: UUID
    field_name: str
    old_value: str | None
    new_value: str | None
    reason: str | None
    updated_by: str
    created_at: str
