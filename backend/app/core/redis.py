"""Async Redis connection pool and client manager."""

from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

_redis_pool: ConnectionPool | None = None


def get_redis_pool() -> ConnectionPool:
    """Retrieve or initialize the global Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
    return _redis_pool


async def get_redis_client() -> Redis:
    """Acquire an async Redis client from the connection pool."""
    return Redis(connection_pool=get_redis_pool())


async def close_redis() -> None:
    """Gracefully terminate the Redis connection pool."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None
