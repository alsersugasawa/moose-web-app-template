"""
Centralised logging configuration for Phase 5.

Call configure_logging() once at application startup (before any other
module emits log records).  All existing logging.getLogger(__name__) calls
in cache.py, tasks.py, worker.py, etc. automatically inherit the handler.

Format options:
  "json"  — structured JSON output (default; recommended for production)
  "text"  — human-readable colourless output (set LOG_FORMAT=text in .env.development)
"""

import logging
import sys
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_access_logger = logging.getLogger("app.access")


def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    """Configure the root logger with a JSON or plain-text formatter."""
    handler = logging.StreamHandler(sys.stdout)

    if fmt == "json":
        try:
            from pythonjsonlogger import jsonlogger
            formatter = jsonlogger.JsonFormatter(
                fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
                rename_fields={
                    "asctime": "timestamp",
                    "levelname": "level",
                    "name": "logger",
                },
            )
            handler.setFormatter(formatter)
        except ImportError:
            # Fallback if python-json-logger is somehow missing
            pass

    logging.basicConfig(
        level=level.upper(),
        handlers=[handler],
        force=True,   # override any existing handlers (e.g. uvicorn's)
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Emit one structured log line per HTTP request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000)

        _access_logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else None,
            },
        )
        return response
