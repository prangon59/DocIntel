"""API v1 master router."""
from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/info", tags=["meta"])
async def get_api_info() -> dict:
    """Return API metadata and status."""
    return {
        "api_version": "v1",
        "description": "AI-Powered Document Intelligence System API",
    }
