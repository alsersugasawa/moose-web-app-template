"""
Task enqueueing helpers (Phase 4).

Each helper enqueues a job on the ARQ Redis queue when the pool is available,
and falls back to calling the underlying function directly (inline) when Redis
is not configured.  This means the application works correctly with or without
a running ARQ worker — no configuration change required for single-instance
development deployments.

Usage
-----
    from app.tasks import enqueue_verification_email, enqueue_password_reset_email

    await enqueue_verification_email(user.email, user.username, token)
"""

import logging
from typing import Optional
from app.settings import settings

logger = logging.getLogger(__name__)

# Module-level ARQ pool — set by init_arq_pool() during app lifespan
_arq_pool: Optional[object] = None


async def init_arq_pool() -> Optional[object]:
    """
    Create and store the ARQ connection pool.
    Called once from the FastAPI lifespan handler.
    Returns None when REDIS_URL is not configured.
    """
    global _arq_pool
    if not settings.redis_url:
        logger.info("[tasks] REDIS_URL not set — email tasks will run inline (no background queue)")
        return None
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        _arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        logger.info("[tasks] ARQ pool ready: %s", settings.redis_url)
        return _arq_pool
    except Exception as exc:
        logger.warning("[tasks] ARQ pool creation failed (%s) — email tasks will run inline", exc)
        _arq_pool = None
        return None


async def close_arq_pool() -> None:
    """Close the ARQ pool on app shutdown."""
    global _arq_pool
    if _arq_pool is not None:
        await _arq_pool.aclose()
        _arq_pool = None


# ── Enqueue helpers ───────────────────────────────────────────────────────────

async def enqueue_verification_email(to: str, username: str, token: str) -> None:
    """
    Send an email-verification link via the ARQ worker queue.
    Falls back to inline send if ARQ is unavailable.
    """
    if _arq_pool is not None:
        await _arq_pool.enqueue_job("send_verification_email_task", to, username, token)
        logger.debug("[tasks] queued send_verification_email for %s", to)
    else:
        from app.email import send_verification_email
        await send_verification_email(to, username, token)


async def enqueue_password_reset_email(to: str, username: str, token: str) -> None:
    """
    Send a password-reset link via the ARQ worker queue.
    Falls back to inline send if ARQ is unavailable.
    """
    if _arq_pool is not None:
        await _arq_pool.enqueue_job("send_password_reset_email_task", to, username, token)
        logger.debug("[tasks] queued send_password_reset_email for %s", to)
    else:
        from app.email import send_password_reset_email
        await send_password_reset_email(to, username, token)
