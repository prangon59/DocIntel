"""ProcessingEvent model tracking pipeline stage execution metrics and errors."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.document import Document


class ProcessingEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Pipeline execution event per stage with timing and status."""

    __tablename__ = "processing_events"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # INGESTION, OCR, EXTRACTION, VALIDATION
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # STARTED, SUCCESS, FAILED
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="processing_events")

    __table_args__ = (Index("ix_processing_events_document_stage", "document_id", "stage"),)
