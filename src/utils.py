"""Shared utilities: request tracing, retry with backoff, circuit breaker."""

from __future__ import annotations

import functools
import time
import uuid
from typing import Any, Callable, Dict, Optional, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class RequestTracer:
    """Extracts or generates a request-ID from HTTP headers."""

    @staticmethod
    def get_request_id_from_headers(headers: Dict[str, str]) -> str:
        for key in ("X-Request-ID", "x-request-id", "X-Amzn-Trace-Id"):
            val = headers.get(key)
            if val:
                return val
        return str(uuid.uuid4())


def retry(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable[[F], F]:
    """Decorator: retry ``fn`` on matching exceptions with exponential backoff."""

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = base_delay
            last_exc: Optional[Exception] = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        time.sleep(delay)
                        delay *= backoff
            raise last_exc  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


class CircuitBreaker:
    """Simple closed/open circuit breaker.

    Opens after ``failure_threshold`` consecutive failures; resets to
    half-open after ``reset_timeout`` seconds.
    """

    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 30.0) -> None:
        self._threshold = failure_threshold
        self._timeout = reset_timeout
        self._failures = 0
        self._opened_at: Optional[float] = None

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= self._timeout:
            self._opened_at = None  # half-open: allow one probe
            return False
        return True

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            self._opened_at = time.monotonic()
