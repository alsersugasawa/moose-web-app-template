"""
Redis cache layer (Phase 4).

Provides a lightweight async cache backed by Redis.  When REDIS_URL is not
configured the helpers are no-ops and callers fall back to direct DB queries —
no code change required in the calling code.

Usage
-----
    from app.cache import get_redis, cache_get, cache_set, cache_delete

    # In a FastAPI endpoint:
    async def my_endpoint(r=Depends(get_redis)):
        data = await cache_get(r, "my:key")
        if data is None:
            data = await fetch_from_db(...)
            await cache_set(r, "my:key", data, ttl=60)
        return data
"""

import json
import logging
from typing import Any, Optional

from app.settings import settings

logger = logging.getLogger(__name__)

# Module-level pool — initialised in app lifespan, cleaned up on shutdown
_redis_pool: Optional[Any] = None   # redis.asyncio.Redis | None


async def init_redis() -> Optional[Any]:
    """
    Create and store the Redis connection pool.
    Called once from the FastAPI lifespan handler.
    Returns None if REDIS_URL is not configured.
    """
    global _redis_pool
    if not settings.redis_url:
        logger.info("[cache] REDIS_URL not set — Redis disabled (in-memory fallback active)")
        return None
    try:
        import redis.asyncio as aioredis
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await _redis_pool.ping()
        logger.info("[cache] Redis connected: %s", settings.redis_url)
        return _redis_pool
    except Exception as exc:
        logger.warning("[cache] Redis connection failed (%s) — falling back to no-cache mode", exc)
        _redis_pool = None
        return None


async def close_redis() -> None:
    """Close the Redis connection pool. Called on app shutdown."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None


async def get_redis() -> Optional[Any]:
    """
    FastAPI dependency that yields the Redis client.
    Returns None when Redis is unavailable — callers must handle the None case.
    """
    return _redis_pool


# ── Cache helpers ─────────────────────────────────────────────────────────────

async def cache_get(r: Optional[Any], key: str) -> Optional[Any]:
    """Return the cached value for *key*, or None on miss / Redis unavailable."""
    if r is None:
        return None
    try:
        raw = await r.get(key)
        return json.loads(raw) if raw is not None else None
    except Exception as exc:
        logger.debug("[cache] cache_get error key=%s: %s", key, exc)
        return None


async def cache_set(r: Optional[Any], key: str, value: Any, ttl: int = 60) -> None:
    """Store *value* under *key* with an expiry of *ttl* seconds."""
    if r is None:
        return
    try:
        await r.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception as exc:
        logger.debug("[cache] cache_set error key=%s: %s", key, exc)


async def cache_delete(r: Optional[Any], *keys: str) -> None:
    """Delete one or more cache keys."""
    if r is None or not keys:
        return
    try:
        await r.delete(*keys)
    except Exception as exc:
        logger.debug("[cache] cache_delete error keys=%s: %s", keys, exc)
