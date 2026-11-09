"""Rate limiter and backoff coordinator for LLM and Embedding API calls.

Ensures strict compliance with Google Gemini free-tier limits (e.g., 15 RPM, concurrency bounds)
across async coroutines and distributed Celery workers via Redis (with local fallback).
Includes exponential backoff with random jitter and Retry-After header/message inspection.
"""

import asyncio
import logging
import random
import re
import time
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from app.core.config import settings

logger = logging.getLogger("docintel.llm.ratelimiter")


def extract_retry_after(exc: Exception) -> float | None:
    """Extract retry-after delay in seconds from exception headers or message."""
    # 1. Check HTTP response headers if available
    response = getattr(exc, "response", None)
    if response is not None:
        headers = getattr(response, "headers", {})
        if isinstance(headers, dict) and "retry-after" in headers:
            try:
                return float(headers["retry-after"])
            except (ValueError, TypeError):
                pass

    # 2. Parse from exception string (e.g. "Resource exhausted... retry after 15s" or "Retry-After: 20")
    msg = str(exc)
    match = re.search(r"retry[\s_-]*(?:in|after)?[\s_:=]*(\d+(?:\.\d+)?)\s*s?", msg, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            pass

    return None


def is_rate_limit_or_quota_error(exc: Exception) -> bool:
    """Check if exception represents an HTTP 429 or quota exhaustion error."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if code in (429, 503):
        return True

    msg = str(exc).upper()
    return any(
        phrase in msg
        for phrase in (
            "429",
            "RESOURCE_EXHAUSTED",
            "RESOURCE EXHAUSTED",
            "EXHAUSTED",
            "QUOTA_EXCEEDED",
            "QUOTA EXCEEDED",
            "QUOTA",
            "RATE_LIMIT",
            "RATE LIMIT",
            "TOO_MANY_REQUESTS",
        )
    )


class LLMRateLimiter:
    """Sliding-window and concurrency rate limiter for LLM API requests."""

    def __init__(
        self,
        max_requests_per_minute: int | None = None,
        concurrency_limit: int | None = None,
        redis_url: str | None = None,
    ) -> None:
        self.rpm = max_requests_per_minute or settings.LLM_MAX_REQUESTS_PER_MINUTE
        self.concurrency = concurrency_limit or settings.LLM_CONCURRENCY_LIMIT
        self.redis_url = redis_url or settings.REDIS_URL

        self._semaphore = asyncio.Semaphore(self.concurrency)
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()
        self._redis_client: Any = None
        self._redis_checked = False

    def _get_redis(self) -> Any:
        """Lazily initialize Redis client for cross-worker synchronization."""
        if not self._redis_checked:
            self._redis_checked = True
            try:
                import redis

                r = redis.from_url(
                    self.redis_url,
                    socket_connect_timeout=0.5,
                    socket_timeout=0.5,
                    decode_responses=True,
                )
                r.ping()
                self._redis_client = r
                logger.info("LLMRateLimiter synchronized via Redis at %s", self.redis_url)
            except Exception:
                self._redis_client = None
                logger.debug("Redis unavailable; using local in-process LLMRateLimiter.")
        return self._redis_client

    async def _acquire_redis(self) -> float:
        """Rate limit using Redis sorted set sliding window across workers."""
        r = self._get_redis()
        wait_time = 0.0
        while True:
            now = time.time()
            pipe = r.pipeline()
            # Remove calls older than 60 seconds
            pipe.zremrangebyscore("ratelimit:llm_rpm", 0, now - 60.0)
            pipe.zcard("ratelimit:llm_rpm")
            _, count = pipe.execute()

            if count < self.rpm:
                # Add current timestamp with unique member
                r.zadd("ratelimit:llm_rpm", {f"{now}:{random.random()}": now})
                r.expire("ratelimit:llm_rpm", 120)
                return wait_time

            # Need to wait until oldest call exits 60-second window
            oldest = r.zrange("ratelimit:llm_rpm", 0, 0, withscores=True)
            sleep_duration = 2.0
            if oldest:
                oldest_score = oldest[0][1]
                sleep_duration = max(0.5, (oldest_score + 60.0) - now + 0.2)

            logger.info("LLM rate limit reached (%d/%d RPM); waiting %.1fs", count, self.rpm, sleep_duration)
            await asyncio.sleep(sleep_duration)
            wait_time += sleep_duration

    async def _acquire_local(self) -> float:
        """Rate limit using in-process sliding window."""
        wait_time = 0.0
        async with self._lock:
            while True:
                now = time.time()
                while self._timestamps and self._timestamps[0] <= now - 60.0:
                    self._timestamps.popleft()

                if len(self._timestamps) < self.rpm:
                    self._timestamps.append(now)
                    return wait_time

                oldest = self._timestamps[0]
                sleep_duration = max(0.5, (oldest + 60.0) - now + 0.2)
                logger.info("LLM local rate limit reached (%d/%d RPM); waiting %.1fs", len(self._timestamps), self.rpm, sleep_duration)
                await asyncio.sleep(sleep_duration)
                wait_time += sleep_duration

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[float]:
        """Acquire a concurrency slot and rate-limit token.

        Yields:
            float: Total time in seconds spent waiting on rate limits.
        """
        start_wait = time.perf_counter()
        await self._semaphore.acquire()
        try:
            r = self._get_redis()
            if r is not None:
                try:
                    await self._acquire_redis()
                except Exception:
                    await self._acquire_local()
            else:
                await self._acquire_local()

            wait_duration = time.perf_counter() - start_wait
            yield wait_duration
        finally:
            self._semaphore.release()


_global_rate_limiter: LLMRateLimiter | None = None


def get_llm_rate_limiter() -> LLMRateLimiter:
    """Retrieve global shared LLMRateLimiter instance."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = LLMRateLimiter()
    return _global_rate_limiter
