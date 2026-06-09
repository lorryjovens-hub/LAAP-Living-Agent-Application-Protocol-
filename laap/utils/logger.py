"""LAAP — Logging System (upgraded with Hermes Agent logging engine)"""

from __future__ import annotations
import logging
import os
import re
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

DEFAULT_LOG_DIR = Path.home() / ".laap" / "logs"

# Patterns for redacting secrets in log messages
_SECRET_PATTERNS = [
    re.compile(r'(sk-[A-Za-z0-9]{20,})'),
    re.compile(r'(Bearer\s+)[A-Za-z0-9_=./+\-]{16,}'),
]

_logging_initialized = False
_session_context = threading.local()


def set_session_context(session_id: str):
    _session_context.id = session_id


def clear_session_context():
    _session_context.id = None


def get_session_context() -> Optional[str]:
    return getattr(_session_context, "id", None)


class RedactingFormatter(logging.Formatter):
    """Log formatter that redacts secrets."""

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        for pattern in _SECRET_PATTERNS:
            msg = pattern.sub(r"\1...[REDACTED]", msg)
        return msg


class SessionContextFilter(logging.Filter):
    """Add session context to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        sid = get_session_context()
        record.session_tag = f"[{sid[:8]}] " if sid else ""
        return True


def setup_logging(log_dir: Optional[Path] = None,
                  level: int = logging.INFO,
                  max_bytes: int = 10 * 1024 * 1024,
                  backup_count: int = 5,
                  console: bool = True,
                  force: bool = False) -> bool:
    """Initialize the logging system. Idempotent unless force=True."""
    global _logging_initialized

    if _logging_initialized and not force:
        return False

    log_path = log_dir or DEFAULT_LOG_DIR
    log_path.mkdir(parents=True, exist_ok=True)

    log_format = "%(asctime)s | %(levelname)-8s | %(session_tag)s%(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger("laap")
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    formatter = RedactingFormatter(fmt=log_format, datefmt=date_format)
    session_filter = SessionContextFilter()

    # agent.log — INFO+
    agent_handler = RotatingFileHandler(
        log_path / "agent.log", maxBytes=max_bytes, backupCount=backup_count,
        encoding="utf-8"
    )
    agent_handler.setLevel(level)
    agent_handler.setFormatter(formatter)
    agent_handler.addFilter(session_filter)
    root.addHandler(agent_handler)

    # errors.log — WARNING+
    error_handler = RotatingFileHandler(
        log_path / "errors.log", maxBytes=max_bytes, backupCount=backup_count,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)
    error_handler.addFilter(session_filter)
    root.addHandler(error_handler)

    # debug.log — DEBUG+
    debug_handler = RotatingFileHandler(
        log_path / "debug.log", maxBytes=max_bytes, backupCount=backup_count,
        encoding="utf-8"
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(formatter)
    debug_handler.addFilter(session_filter)
    root.addHandler(debug_handler)

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(RedactingFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(session_tag)s%(message)s",
            datefmt="%H:%M:%S"
        ))
        console_handler.addFilter(session_filter)
        root.addHandler(console_handler)

    # Quiet noisy libraries
    for lib in ["httpx", "httpcore", "urllib3", "openai", "anthropic"]:
        logging.getLogger(lib).setLevel(logging.WARNING)

    _logging_initialized = True
    logger = logging.getLogger("laap.logger")
    logger.info(f"Logging initialized: {log_path}")
    return True


def get_logger(name: str) -> logging.Logger:
    """Get a namespaced LAAP logger."""
    return logging.getLogger(f"laap.{name}")


# Backward compatibility
class LAAPLogger:
    _instances = {}

    @classmethod
    def get(cls, name: str, level=logging.INFO) -> logging.Logger:
        if name in cls._instances:
            return cls._instances[name]
        logger = get_logger(name)
        logger.setLevel(level)
        cls._instances[name] = logger
        return logger
