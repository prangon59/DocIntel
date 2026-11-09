"""ValidationIssue model tracking mathematical, completeness, and duplicate anomalies."""

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.document import Document


class IssueSeverity(StrEnum):
    """Severity levels for validation findings."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class ValidationIssue(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Validation issue found by deterministic rules."""

    __tablename__ = "validation_issues"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # e.g., MATH_MISMATCH, DUPLICATE_INVOICE
    severity: Mapped[IssueSeverity] = mapped_column(
        SQLEnum(IssueSeverity, name="issue_severity_enum"),
        default=IssueSeverity.WARNING,
        nullable=False,
        index=True,
    )
    field: Mapped[str] = mapped_column(String(64), default="general", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="validation_issues")

    __table_args__ = (Index("ix_validation_document_severity", "document_id", "severity"),)
