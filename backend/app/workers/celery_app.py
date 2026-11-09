"""Celery application instance configuration."""

from celery import Celery  # type: ignore[import-untyped]

from app.core.config import settings

celery_app = Celery(
    "docintel_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes hard limit for massive 1000-page docs
    task_soft_time_limit=1500,  # 25 minutes soft limit
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=False,
    broker_connection_max_retries=1,
    broker_transport_options={
        "max_retries": 1,
        "socket_timeout": 1.0,
        "socket_connect_timeout": 1.0,
    },
)

celery_app.autodiscover_tasks(["app.workers"])
