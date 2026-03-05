"""
Prometheus metrics for Phase 5.

Module-level singletons are safe because prometheus_client uses a global
default registry; defining them here means any import order works.

Usage:
    from app.metrics import PrometheusMiddleware, start_pool_gauge_updater
"""

import asyncio
import time
from typing import Callable

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ── Counters & histograms ─────────────────────────────────────────────────────

http_requests_total = Counter(
    "webapp_http_requests_total",
    "Total number of HTTP requests",
    ["method", "path", "status_code"],
)

http_request_duration_seconds = Histogram(
    "webapp_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

# ── DB connection pool gauges ─────────────────────────────────────────────────

db_pool_size = Gauge(
    "webapp_db_pool_size",
    "Configured SQLAlchemy connection pool size",
)
db_pool_checkedout = Gauge(
    "webapp_db_pool_checkedout",
    "SQLAlchemy pool connections currently in use",
)
db_pool_overflow = Gauge(
    "webapp_db_pool_overflow",
    "SQLAlchemy pool overflow connections currently in use",
)

# Paths excluded from request instrumentation (to avoid noise in dashboards)
_SKIP_PATHS = {"/metrics", "/health", "/health/detailed"}


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Record request count and latency for every HTTP request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path in _SKIP_PATHS:
            return await call_next(request)

        method = request.method
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        status = str(response.status_code)
        http_requests_total.labels(method=method, path=path, status_code=status).inc()
        http_request_duration_seconds.labels(method=method, path=path).observe(duration)

        return response


async def _pool_gauge_loop(engine, interval: int = 15) -> None:
    """Background task: refresh DB pool gauges every `interval` seconds."""
    while True:
        try:
            pool = engine.pool
            db_pool_size.set(pool.size())
            db_pool_checkedout.set(pool.checkedout())
            db_pool_overflow.set(pool.overflow())
        except Exception:
            pass
        await asyncio.sleep(interval)


def start_pool_gauge_updater(engine) -> asyncio.Task:
    """Schedule the pool gauge loop as an asyncio background task."""
    return asyncio.create_task(_pool_gauge_loop(engine))


def metrics_response() -> Response:
    """Return a Prometheus text-format metrics response."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
