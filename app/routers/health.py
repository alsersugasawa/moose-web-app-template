"""
Health check endpoints for Phase 5.

GET /health           — fast liveness probe (no DB I/O); unchanged behaviour
GET /health/detailed  — readiness probe; checks DB, Redis, and ARQ queue
GET /metrics          — Prometheus text-format metrics (when enabled)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.admin import APP_VERSION
from app.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", include_in_schema=False)
async def health_liveness():
    """Fast liveness probe — no dependency checks."""
    return {"status": "healthy"}


@router.get("/health/detailed")
async def health_detailed(request: Request):
    """
    Readiness probe that checks all runtime dependencies.

    Returns HTTP 200 with status="healthy" when all required dependencies
    are reachable, or status="degraded" when optional ones (Redis, worker)
    are unavailable.  Returns HTTP 503 only when the database is unreachable.
    """
    checks: dict[str, dict] = {}

    # ── Database ──────────────────────────────────────────────────────────────
    db_ok = False
    try:
        from app.database import async_session_maker
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
        db_ok = True
    except Exception as exc:
        logger.error("Health check: database unreachable", extra={"error": str(exc)})
        checks["database"] = {"status": "error", "detail": str(exc)}

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis = getattr(request.app.state, "redis", None)
    if redis is not None:
        try:
            await redis.ping()
            checks["redis"] = {"status": "ok"}
        except Exception as exc:
            logger.warning("Health check: Redis unreachable", extra={"error": str(exc)})
            checks["redis"] = {"status": "error", "detail": str(exc)}
    else:
        checks["redis"] = {"status": "disabled"}

    # ── ARQ worker queue ──────────────────────────────────────────────────────
    try:
        from app.tasks import _arq_pool  # type: ignore[attr-defined]
        if _arq_pool is not None:
            info = await _arq_pool.info()
            checks["worker_queue"] = {
                "status": "ok",
                "queued_jobs": info.get("jobs_queued", 0),
            }
        else:
            checks["worker_queue"] = {"status": "disabled"}
    except Exception as exc:
        logger.warning("Health check: ARQ queue error", extra={"error": str(exc)})
        checks["worker_queue"] = {"status": "error", "detail": str(exc)}

    # ── Overall status ────────────────────────────────────────────────────────
    overall = (
        "healthy"
        if all(v["status"] in ("ok", "disabled") for v in checks.values())
        else "degraded"
    )

    payload = {"status": overall, "checks": checks, "version": APP_VERSION}

    if not db_ok:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content=payload)

    return payload


# ── Prometheus metrics ────────────────────────────────────────────────────────

if settings.prometheus_enabled:
    @router.get("/metrics", include_in_schema=False)
    async def prometheus_metrics():
        """Prometheus scrape endpoint — returns text/plain metrics."""
        from app.metrics import metrics_response
        return metrics_response()
