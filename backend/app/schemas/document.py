"""Document API Pydantic request and response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentRead(BaseModel):
    """Document summary payload."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    file_type: str
    mime_type: str
    file_size: int
    file_hash: str
    status: str
    page_count: int
    needs_review: bool
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class PageRead(BaseModel):
    """Extracted text page payload."""

    model_config = ConfigDict(from_attributes=True)

    page_number: int
    raw_text: str
    extraction_method: str
    ocr_confidence: float | None = None
    char_count: int


class DocumentDetailResponse(DocumentRead):
    """Detailed document response including extracted pages."""

    pages: list[PageRead] = Field(default_factory=list)


class DocumentUploadItem(BaseModel):
    """Per-file upload tracking receipt."""

    id: uuid.UUID
    filename: str
    status: str
    job_id: str


class DocumentUploadResponse(BaseModel):
    """Batch upload submission result."""

    uploaded: list[DocumentUploadItem]
    total_files: int
    message: str


class DocumentStatusResponse(BaseModel):
    """Live document processing progress status."""

    document_id: uuid.UUID
    status: str
    stage: str
    pages_done: int
    pages_total: int
    percentage: float
    error_message: str | None = None


class DocumentListResponse(BaseModel):
    """Paginated documents response."""

    items: list[DocumentRead]
    total: int
    skip: int
    limit: int
