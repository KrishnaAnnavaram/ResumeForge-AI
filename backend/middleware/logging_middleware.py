"""
middleware/logging_middleware.py — Per-request structured logging.

Assigns a UUID correlation_id to every request and logs method, path,
status code, and duration on completion.
"""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.core.logger import get_logger, set_correlation_id

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        cid = str(uuid.uuid4())
        set_correlation_id(cid)

        start = time.perf_counter()
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else "unknown",
        )

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        # Propagate correlation ID to client for tracing
        response.headers["X-Correlation-ID"] = cid
        return response
