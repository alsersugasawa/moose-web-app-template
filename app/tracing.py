"""
OpenTelemetry tracing initialisation for Phase 5.

Only activated when both OTEL_ENABLED=true and OTEL_ENDPOINT is set.
Everything is a no-op when OTel is disabled, so zero-config deployments
are unaffected.

Usage (in lifespan):
    from app.tracing import init_tracing
    init_tracing(app, engine)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def init_tracing(app, engine) -> None:
    """
    Bootstrap the OpenTelemetry SDK and auto-instrument FastAPI + SQLAlchemy.

    Parameters
    ----------
    app:    The FastAPI application instance.
    engine: The SQLAlchemy async engine (from app.database).
    """
    from app.settings import settings

    if not settings.otel_enabled or not settings.otel_endpoint:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    except ImportError as exc:
        logger.warning("OpenTelemetry packages not available: %s", exc)
        return

    resource = Resource(attributes={"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.otel_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_global_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)

    # SQLAlchemy instrumentation requires the sync engine handle
    try:
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    except Exception:
        # async-only engines may not expose sync_engine; skip gracefully
        pass

    logger.info(
        "OpenTelemetry tracing enabled",
        extra={"service_name": settings.otel_service_name, "endpoint": settings.otel_endpoint},
    )


def get_tracer(name: str = "app"):
    """Return the global tracer (no-op tracer if OTel is not initialised)."""
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        return _NoOpTracer()


class _NoOpTracer:
    """Fallback tracer that does nothing — used when OTel is disabled."""

    def start_as_current_span(self, name, **_kwargs):
        from contextlib import nullcontext
        return nullcontext()
