"""Embedding model for pgvector semantic search."""

import uuid
from typing import TYPE_CHECKING, Optional

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.page import Page


class Embedding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Text chunk vector embedding stored via pgvector."""

    __tablename__ = "embeddings"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pages.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(768), nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="embeddings")
    page: Mapped[Optional["Page"]] = relationship("Page", back_populates="embeddings")
