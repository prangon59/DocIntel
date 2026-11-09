"""Correction model recording human audit history for edited extracted fields."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.document import Document


class Correction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Audit log of human corrections to extracted document fields."""

    __tablename__ = "corrections"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    updated_by: Mapped[str] = mapped_column(String(128), default="reviewer", nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="corrections")
