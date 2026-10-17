"""Structured logging that avoids leaking secrets or private request bodies."""

from __future__ import annotations

import logging
import re
import sys

_REDACTIONS = (
    re.compile(r"(?i)(api[_-]?key\"?\s*[:=]\s*\"?)([^\s\",}]+)"),
    re.compile(r"(?i)(authorization\"?\s*[:=]\s*\"?)(bearer\s+)?([^\s\",}]+)"),
    re.compile(r"(?i)(token\"?\s*[:=]\s*\"?)([^\s\",}]+)"),
    re.compile(r"(?i)(password\"?\s*[:=]\s*\"?)([^\s\",}]+)"),
    re.compile(r"(?i)(private_key\"?\s*[:=]\s*\"?)([^\s\",}]+)"),
)


class RedactingFormatter(logging.Formatter):
    """Masks credential-shaped substrings before anything reaches a log sink."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        for pattern in _REDACTIONS:
            message = pattern.sub(lambda m: m.group(1) + "***", message)
        return message


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(
        RedactingFormatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # Uvicorn installs its own noisy access logger; keep it but align the level.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
