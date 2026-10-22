"""Fixed-window rate limiter with Redis (shared) or in-memory (single process) storage."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after: int


class RateLimiter(Protocol):
    async def hit(self, key: str, limit: int, window_seconds: int) -> RateLimitResult: ...


class MemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, tuple[int, float]] = {}

    async def hit(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        now = time.monotonic()
        count, reset_at = self._buckets.get(key, (0, now + window_seconds))
        if now >= reset_at:
            count, reset_at = 0, now + window_seconds
        count += 1
        self._buckets[key] = (count, reset_at)
        if len(self._buckets) > 10_000:  # crude eviction for long-running dev servers
            for k, (_, r) in list(self._buckets.items()):
                if now >= r:
                    del self._buckets[k]
        retry = int(reset_at - now) + 1
        return RateLimitResult(count <= limit, max(0, limit - count), retry if count > limit else 0)

    async def reset(self, key: str) -> None:
        self._buckets.pop(key, None)


class RedisRateLimiter:
    def __init__(self, redis) -> None:  # type: ignore[no-untyped-def]
        self.redis = redis

    async def hit(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        name = f"rl:{key}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(name)
            pipe.ttl(name)
            count, ttl = await pipe.execute()
        if ttl is None or ttl < 0:
            await self.redis.expire(name, window_seconds)
            ttl = window_seconds
        allowed = count <= limit
        return RateLimitResult(allowed, max(0, limit - count), int(ttl) if not allowed else 0)

    async def reset(self, key: str) -> None:
        await self.redis.delete(f"rl:{key}")
