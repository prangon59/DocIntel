"""Extraction and LineItem models representing AI-extracted structured invoice data."""

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, Float, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.document import Document


class Extraction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Structured extraction record for an invoice."""

    __tablename__ = "extractions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Financial money amounts: strict Decimal
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    tax: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)  # ISO 4217

    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    raw_llm_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), default="v1.0", nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="extractions")
    line_items: Mapped[list["LineItem"]] = relationship(
        "LineItem", back_populates="extraction", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_extractions_supplier_invoice", "supplier_name", "invoice_number"),)


class LineItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Individual line item belonging to an extracted invoice."""

    __tablename__ = "line_items"

    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extractions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    line_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Relationships
    extraction: Mapped["Extraction"] = relationship("Extraction", back_populates="line_items")
