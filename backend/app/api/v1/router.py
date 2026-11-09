"""API v1 master router."""

from fastapi import APIRouter

from app.api.v1.crossverify import router as crossverify_router
from app.api.v1.documents import router as documents_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.search import router as search_router

api_router = APIRouter()
api_router.include_router(documents_router)
api_router.include_router(search_router)
api_router.include_router(crossverify_router)
api_router.include_router(metrics_router)
api_router.include_router(jobs_router)


@api_router.get("/info", tags=["meta"])
async def get_api_info() -> dict:
    """Return API metadata and status."""
    return {
        "api_version": "v1",
        "description": "AI-Powered Document Intelligence System API",
    }
