"""@timed decorator — converts exceptions into structured error dicts."""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def timed(tool_name: str) -> Callable[[F], F]:
    """Wrap a tool function so every exception becomes an error dict.

    The contract:
      - On success: return value is whatever the tool returns (a dict).
      - On exception: return ``{tool_name, duration_ms, error_code, error_message}``.
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            try:
                result = fn(*args, **kwargs)
                duration_ms = int((time.monotonic() - start) * 1000)
                if isinstance(result, dict):
                    result.setdefault("tool_name", tool_name)
                    result.setdefault("duration_ms", duration_ms)
                return result
            except Exception as exc:  # noqa: BLE001
                duration_ms = int((time.monotonic() - start) * 1000)
                return {
                    "tool_name": tool_name,
                    "duration_ms": duration_ms,
                    "error_code": "TOOL_EXCEPTION",
                    "error_message": str(exc),
                }

        return wrapper  # type: ignore[return-value]

    return decorator
