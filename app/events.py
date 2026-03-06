"""
Lightweight synchronous pub/sub event bus for Phase 6.

Usage:
    from app.events import on, emit

    # Register handler (typically in lifespan)
    on("user.registered", lambda user_id, email: ...)

    # Emit event (in routers / tasks)
    emit("user.registered", user_id=user.id, email=user.email)

Handlers are called synchronously in registration order.
Exceptions in handlers are swallowed — they never crash the caller.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)

_handlers: dict[str, list[Callable]] = defaultdict(list)


def on(event: str, handler: Callable) -> None:
    """Register *handler* to be called whenever *event* is emitted."""
    _handlers[event].append(handler)


def emit(event: str, **data: Any) -> None:
    """Call all handlers registered for *event*, passing **data** as kwargs."""
    for handler in _handlers.get(event, []):
        try:
            handler(**data)
        except Exception as exc:
            logger.warning(
                "Event handler raised an exception",
                extra={"event": event, "handler": handler.__name__, "error": str(exc)},
            )
