"""Health check response schemas."""

from pydantic import BaseModel, Field


class ServiceHealth(BaseModel):
    """Component status details."""

    status: str = Field(..., description="ok or error")
    details: str | None = Field(
        default=None, description="Additional status detail or error string"
    )


class HealthResponse(BaseModel):
    """System health check payload."""

    status: str = Field("ok", description="Overall system health status (ok, degraded, error)")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Operating environment")
    components: dict[str, ServiceHealth] = Field(
        default_factory=dict,
        description="Status of dependencies",
    )
