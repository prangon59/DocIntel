"""Unit and integration tests for operational metrics reporting."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.event import ProcessingEvent
from app.models.validation import IssueSeverity, ValidationIssue
from app.services.metrics.service import compute_operational_metrics


@pytest.fixture
async def seed_metrics_data(db_session: AsyncSession):
    # 3 Completed documents (1 needs review)
    d1 = Document(
        id=uuid.uuid4(),
        filename="doc1.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=100,
        file_hash="h1",
        storage_path="p1",
        status=DocumentStatus.COMPLETED,
        needs_review=False,
    )
    d2 = Document(
        id=uuid.uuid4(),
        filename="doc2.png",
        file_type="png",
        mime_type="image/png",
        file_size=200,
        file_hash="h2",
        storage_path="p2",
        status=DocumentStatus.COMPLETED,
        needs_review=True,
    )
    d3 = Document(
        id=uuid.uuid4(),
        filename="doc3.xlsx",
        file_type="xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size=300,
        file_hash="h3",
        storage_path="p3",
        status=DocumentStatus.COMPLETED,
        needs_review=False,
    )

    # 1 Failed document
    d4 = Document(
        id=uuid.uuid4(),
        filename="doc4.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=400,
        file_hash="h4",
        storage_path="p4",
        status=DocumentStatus.FAILED,
        error_message="Corrupted file header",
        needs_review=False,
    )

    db_session.add_all([d1, d2, d3, d4])
    await db_session.flush()

    # Validation issues on d2
    i1 = ValidationIssue(
        document_id=d2.id,
        code="MATH_MISMATCH_TOTAL",
        severity=IssueSeverity.ERROR,
        field="total",
        message="Math mismatch",
        details={},
    )
    i2 = ValidationIssue(
        document_id=d2.id,
        code="LOW_CONFIDENCE",
        severity=IssueSeverity.WARNING,
        field="general",
        message="Low confidence",
        details={},
    )
    db_session.add_all([i1, i2])

    # Processing events with durations: 100ms, 200ms, 300ms
    e1 = ProcessingEvent(document_id=d1.id, stage="PIPELINE", status="SUCCESS", duration_ms=100.0)
    e2 = ProcessingEvent(document_id=d2.id, stage="PIPELINE", status="SUCCESS", duration_ms=200.0)
    e3 = ProcessingEvent(document_id=d3.id, stage="PIPELINE", status="SUCCESS", duration_ms=300.0)
    db_session.add_all([e1, e2, e3])

    await db_session.commit()
    return d1, d2, d3, d4


@pytest.mark.asyncio
async def test_compute_operational_metrics(db_session: AsyncSession, seed_metrics_data):
    metrics = await compute_operational_metrics(db_session)

    # 4 total documents
    assert metrics.total_documents == 4
    # 3 completed, 1 failed -> 75% success, 25% failure
    assert metrics.completed_count == 3
    assert metrics.failed_count == 1
    assert metrics.success_rate_percentage == 75.0
    assert metrics.failure_rate_percentage == 25.0

    # 1 needs review out of 4 -> 25%
    assert metrics.needs_review_count == 1
    assert metrics.needs_review_percentage == 25.0

    # Validation issues
    assert metrics.total_validation_issues == 2
    assert metrics.issues_by_severity.get("ERROR") == 1
    assert metrics.issues_by_severity.get("WARNING") == 1
    assert metrics.issues_by_code.get("MATH_MISMATCH_TOTAL") == 1
    assert metrics.issues_by_code.get("LOW_CONFIDENCE") == 1

    # Processing durations: average of [100, 200, 300] = 200ms
    assert metrics.avg_processing_time_ms == 200.0
    assert metrics.p95_processing_time_ms > 0.0


@pytest.mark.asyncio
async def test_metrics_endpoint(async_client: AsyncClient, seed_metrics_data):
    response = await async_client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()

    assert data["total_documents"] == 4
    assert data["success_rate_percentage"] == 75.0
    assert data["failure_rate_percentage"] == 25.0
    assert data["needs_review_count"] == 1
    assert data["avg_processing_time_ms"] == 200.0
