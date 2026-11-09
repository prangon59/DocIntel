"""Main FastAPI application entrypoint."""

import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import __version__
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.logging import logger, request_id_ctx, setup_logging
from app.core.redis import close_redis, get_redis_client
from app.schemas.health import HealthResponse, ServiceHealth


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown hooks."""
    setup_logging()
    logger.info(
        "Initializing %s v%s in %s mode...",
        settings.PROJECT_NAME,
        __version__,
        settings.APP_ENV,
    )
    yield
    logger.info("Shutting down %s...", settings.PROJECT_NAME)
    await close_redis()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=__version__,
    description=(
        "Production-grade AI-powered document intelligence and invoice extraction platform."
    ),
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next) -> Response:
    """Inject request ID, track processing latency, and log requests."""
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = request_id_ctx.set(req_id)
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"

        logger.info(
            "%s %s -> %d (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.exception("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred while processing the request.",
                    "request_id": req_id,
                }
            },
            headers={"X-Request-ID": req_id},
        )
    finally:
        request_id_ctx.reset(token)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Check health of the API server and its downstream dependencies (PostgreSQL, Redis)."""
    components: dict[str, ServiceHealth] = {}
    overall_status = "ok"

    # Database health check
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        components["postgres"] = ServiceHealth(status="ok")
    except Exception as exc:
        components["postgres"] = ServiceHealth(status="error", details=str(exc))
        overall_status = "degraded"

    # Redis health check
    try:
        redis_client = await get_redis_client()
        await redis_client.ping()
        components["redis"] = ServiceHealth(status="ok")
    except Exception as exc:
        components["redis"] = ServiceHealth(status="error", details=str(exc))
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        version=__version__,
        environment=settings.APP_ENV,
        components=components,
    )


# Mount versioned API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
