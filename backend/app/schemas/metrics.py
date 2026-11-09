"""Operational metrics schemas reporting genuine system statistics computed from DB."""

from pydantic import BaseModel, ConfigDict, Field


class OperationalMetricsResponse(BaseModel):
    """Aggregate operational system metrics."""

    model_config = ConfigDict(extra="ignore")

    total_documents: int
    status_counts: dict[str, int]
    file_type_counts: dict[str, int]
    completed_count: int
    failed_count: int
    success_rate_percentage: float = Field(
        description="Percentage of completed vs completed + failed"
    )
    failure_rate_percentage: float = Field(description="Percentage of failed vs completed + failed")
    needs_review_count: int
    needs_review_percentage: float
    total_validation_issues: int
    issues_by_severity: dict[str, int]
    issues_by_code: dict[str, int]
    avg_processing_time_ms: float = Field(description="Average processing event duration in ms")
    p95_processing_time_ms: float = Field(
        description="95th percentile processing event duration in ms"
    )
