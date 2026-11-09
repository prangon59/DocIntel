"""Operational metrics calculation service querying actual database statistics without fabrication."""

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.event import ProcessingEvent
from app.models.validation import ValidationIssue
from app.schemas.metrics import OperationalMetricsResponse


async def compute_operational_metrics(db: AsyncSession) -> OperationalMetricsResponse:
    """Calculate genuine live operational metrics from database tables."""
    # 1. Total documents
    total_docs = (await db.execute(select(func.count(Document.id)))).scalar() or 0

    # 2. Status counts
    status_query = select(Document.status, func.count(Document.id)).group_by(Document.status)
    status_rows = (await db.execute(status_query)).all()
    status_counts = {s.value: 0 for s in DocumentStatus}
    for row_status, count in status_rows:
        if row_status:
            status_counts[row_status.value] = count

    completed_count = status_counts.get(DocumentStatus.COMPLETED.value, 0)
    failed_count = status_counts.get(DocumentStatus.FAILED.value, 0)
    finished_count = completed_count + failed_count

    success_rate = (completed_count / finished_count * 100.0) if finished_count > 0 else 0.0
    failure_rate = (failed_count / finished_count * 100.0) if finished_count > 0 else 0.0

    # 3. File type counts
    file_type_query = select(Document.file_type, func.count(Document.id)).group_by(Document.file_type)
    file_type_rows = (await db.execute(file_type_query)).all()
    file_type_counts = {ft: count for ft, count in file_type_rows if ft}

    # 4. Needs review counts
    needs_review_query = select(func.count(Document.id)).where(Document.needs_review == True)  # noqa: E712
    needs_review_count = (await db.execute(needs_review_query)).scalar() or 0
    needs_review_pct = (needs_review_count / total_docs * 100.0) if total_docs > 0 else 0.0

    # 5. Validation issues counts
    total_issues = (await db.execute(select(func.count(ValidationIssue.id)))).scalar() or 0

    severity_query = select(ValidationIssue.severity, func.count(ValidationIssue.id)).group_by(ValidationIssue.severity)
    severity_rows = (await db.execute(severity_query)).all()
    issues_by_severity = {getattr(sev, "value", str(sev)): count for sev, count in severity_rows if sev}

    code_query = select(ValidationIssue.code, func.count(ValidationIssue.id)).group_by(ValidationIssue.code)
    code_rows = (await db.execute(code_query)).all()
    issues_by_code = {code: count for code, count in code_rows if code}

    # 6. Processing duration metrics
    durations_query = select(ProcessingEvent.duration_ms).where(ProcessingEvent.duration_ms.isnot(None))
    duration_rows = (await db.execute(durations_query)).scalars().all()

    durations = [float(d) for d in duration_rows if d is not None and d > 0]
    if durations:
        avg_duration = float(np.mean(durations))
        p95_duration = float(np.percentile(durations, 95))
    else:
        avg_duration = 0.0
        p95_duration = 0.0

    return OperationalMetricsResponse(
        total_documents=total_docs,
        status_counts=status_counts,
        file_type_counts=file_type_counts,
        completed_count=completed_count,
        failed_count=failed_count,
        success_rate_percentage=round(success_rate, 2),
        failure_rate_percentage=round(failure_rate, 2),
        needs_review_count=needs_review_count,
        needs_review_percentage=round(needs_review_pct, 2),
        total_validation_issues=total_issues,
        issues_by_severity=issues_by_severity,
        issues_by_code=issues_by_code,
        avg_processing_time_ms=round(avg_duration, 2),
        p95_processing_time_ms=round(p95_duration, 2),
    )
