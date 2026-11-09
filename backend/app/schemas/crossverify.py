"""Cross-verification schemas for matching and reconciling invoices across documents."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DiscrepancyItem(BaseModel):
    """Specific discrepancy between two matched invoice documents."""

    model_config = ConfigDict(extra="ignore")

    field: str
    value_a: Any = None
    value_b: Any = None
    difference: str | None = None
    severity: str = "ERROR"  # ERROR | WARNING
    message: str


class CrossVerificationReport(BaseModel):
    """Detailed reconciliation report comparing two document extractions."""

    model_config = ConfigDict(extra="ignore")

    document_a_id: UUID
    document_b_id: UUID
    document_a_filename: str
    document_b_filename: str
    supplier_name: str | None = None
    invoice_number: str | None = None
    matched: bool = False
    is_concordant: bool = True
    discrepancies: list[DiscrepancyItem] = Field(default_factory=list)
    summary: str


class CrossVerificationRequest(BaseModel):
    """Request payload to cross-verify two specific documents."""

    model_config = ConfigDict(extra="ignore")

    document_id_a: UUID
    document_id_b: UUID


class CrossVerificationBatchRequest(BaseModel):
    """Request payload to cross-verify all pairwise combinations in a list of documents."""

    model_config = ConfigDict(extra="ignore")

    document_ids: list[UUID]
