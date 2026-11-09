"""Document model tracking file metadata, storage location, and processing status."""

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Index, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.correction import Correction
    from app.models.embedding import Embedding
    from app.models.event import ProcessingEvent
    from app.models.extraction import Extraction
    from app.models.page import Page
    from app.models.validation import ValidationIssue


class DocumentStatus(StrEnum):
    """Processing lifecycle states of a document."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Uploaded business document record."""

    __tablename__ = "documents"

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # pdf, png, jpg, tiff, xlsx, xls, csv
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)

    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus, name="document_status_enum"),
        default=DocumentStatus.PENDING,
        nullable=False,
        index=True,
    )
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Relationships
    pages: Mapped[list["Page"]] = relationship(
        "Page", back_populates="document", cascade="all, delete-orphan", order_by="Page.page_number"
    )
    extractions: Mapped[list["Extraction"]] = relationship(
        "Extraction", back_populates="document", cascade="all, delete-orphan"
    )
    validation_issues: Mapped[list["ValidationIssue"]] = relationship(
        "ValidationIssue", back_populates="document", cascade="all, delete-orphan"
    )
    corrections: Mapped[list["Correction"]] = relationship(
        "Correction", back_populates="document", cascade="all, delete-orphan"
    )
    processing_events: Mapped[list["ProcessingEvent"]] = relationship(
        "ProcessingEvent", back_populates="document", cascade="all, delete-orphan"
    )
    embeddings: Mapped[list["Embedding"]] = relationship(
        "Embedding", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_documents_status_needs_review", "status", "needs_review"),)
