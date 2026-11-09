"""Metrics API endpoint reporting genuine operational performance and error statistics."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.metrics import OperationalMetricsResponse
from app.services.metrics.service import compute_operational_metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get(
    "",
    response_model=OperationalMetricsResponse,
    summary="Retrieve operational performance, accuracy, failure rate, and processing time metrics.",
)
async def get_metrics(
    db: AsyncSession = Depends(get_db_session),
) -> OperationalMetricsResponse:
    """Compute and return genuine operational metrics directly from system database tables."""
    return await compute_operational_metrics(db)
