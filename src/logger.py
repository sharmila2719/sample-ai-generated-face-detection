"""Structured JSON logging helpers."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional


class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge any extra fields passed via `extra={...}`
        for key, val in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "levelname", "levelno", "lineno",
                "message", "module", "msecs", "msg", "name", "pathname",
                "process", "processName", "relativeCreated", "stack_info",
                "thread", "threadName",
            }:
                log_obj[key] = val
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, default=str)


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Return a logger that emits structured JSON to stdout."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False
    return logger


class ContextLogger:
    """Wraps a logger and injects a ``request_id`` into every record."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._ctx: dict[str, Any] = {}

    def set_context(self, **kwargs: Any) -> None:
        self._ctx.update(kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        self._logger.info(msg, extra={**self._ctx, **kwargs})

    def warning(self, msg: str, **kwargs: Any) -> None:
        self._logger.warning(msg, extra={**self._ctx, **kwargs})

    def error(self, msg: str, **kwargs: Any) -> None:
        self._logger.error(msg, extra={**self._ctx, **kwargs})

    def debug(self, msg: str, **kwargs: Any) -> None:
        self._logger.debug(msg, extra={**self._ctx, **kwargs})
