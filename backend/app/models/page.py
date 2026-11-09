"""Page model holding extracted or OCR text per document page."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.embedding import Embedding


class Page(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Single page within a document with extracted text."""

    __tablename__ = "pages"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    extraction_method: Mapped[str] = mapped_column(
        String(64), nullable=False, default="digital_pdf"
    )  # digital_pdf, tesseract_ocr, excel_sheet
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="pages")
    embeddings: Mapped[list["Embedding"]] = relationship(
        "Embedding", back_populates="page", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_pages_document_page_number", "document_id", "page_number", unique=True),
    )
