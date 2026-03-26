"""
core/circuit_breaker.py — Per-provider circuit breaker.

States: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing recovery)

Usage:
    cb = get_circuit_breaker("claude")
    async with cb:
        result = await call_claude(...)
"""

import asyncio
import time
from enum import Enum
from typing import Dict

from backend.core.config import get_settings
from backend.core.exceptions import CircuitOpenError
from backend.core.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class State(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, name: str) -> None:
        self.name = name
        self._state = State.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._lock = asyncio.Lock()

        self._failure_threshold = settings.circuit_breaker_failure_threshold
        self._reset_timeout = settings.circuit_breaker_reset_timeout

    @property
    def state(self) -> State:
        return self._state

    async def __aenter__(self) -> "CircuitBreaker":
        async with self._lock:
            await self._check_state()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        async with self._lock:
            if exc_type is not None and not issubclass(exc_type, CircuitOpenError):
                await self._on_failure()
                return False  # re-raise the original exception
            if exc_type is None:
                await self._on_success()
        return False

    async def _check_state(self) -> None:
        now = time.monotonic()
        if self._state == State.OPEN:
            elapsed = now - self._last_failure_time
            if elapsed >= self._reset_timeout:
                logger.info(
                    "Circuit breaker moving to HALF_OPEN",
                    provider=self.name,
                    elapsed=round(elapsed, 1),
                )
                self._state = State.HALF_OPEN
            else:
                remaining = round(self._reset_timeout - elapsed, 1)
                raise CircuitOpenError(
                    f"Circuit open for '{self.name}'. Retry in {remaining}s.",
                    detail=f"failure_count={self._failure_count}",
                )

    async def _on_success(self) -> None:
        if self._state != State.CLOSED:
            logger.info(
                "Circuit breaker CLOSED (recovered)",
                provider=self.name,
            )
        self._state = State.CLOSED
        self._failure_count = 0

    async def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._failure_threshold:
            if self._state != State.OPEN:
                logger.error(
                    "Circuit breaker OPENED",
                    provider=self.name,
                    failure_count=self._failure_count,
                )
            self._state = State.OPEN


# ── Global registry ───────────────────────────────────────────────────────────
_registry: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    if name not in _registry:
        _registry[name] = CircuitBreaker(name)
    return _registry[name]
