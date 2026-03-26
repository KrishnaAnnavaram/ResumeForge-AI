"""
core/logger.py — Structured JSON logging with correlation ID support.

Every log record includes:
  - timestamp (ISO 8601)
  - level
  - correlation_id  (set per-request via context var)
  - logger name
  - message + any extra kwargs

Usage:
    from backend.core.logger import get_logger, set_correlation_id
    logger = get_logger(__name__)
    logger.info("ATS analysis complete", user_id=uid, score=87.3, tokens=1240)
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from backend.core.config import get_settings

# ── Correlation ID context variable ─────────────────────────────────────────
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def set_correlation_id(cid: str) -> None:
    _correlation_id.set(cid)


def get_correlation_id() -> str:
    return _correlation_id.get()


# ── JSON formatter ────────────────────────────────────────────────────────────
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "correlation_id": get_correlation_id(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge any extra kwargs passed to logger.info(..., key=val)
        for key, val in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "module", "msecs", "message", "msg", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName", "taskName",
            }:
                payload[key] = val
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


# ── Handler wiring ────────────────────────────────────────────────────────────
def _configure_root_logger() -> None:
    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())


_configure_root_logger()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
