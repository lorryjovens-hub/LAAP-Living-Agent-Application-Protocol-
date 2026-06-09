"""
LAAP — Error Classification (ported from Hermes Agent)

Systematic error categorization for handling and recovery.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional


class ErrorCategory(Enum):
    """Categories for classifying errors."""
    API = "api"                   # LLM API errors (auth, rate limit, timeout)
    NETWORK = "network"           # Network connectivity issues
    AUTHENTICATION = "auth"       # API key / auth failures
    RATE_LIMIT = "rate_limit"     # Rate limiting
    TIMEOUT = "timeout"           # Request timeout
    TOOL = "tool"                 # Tool execution errors
    FILE = "file"                 # File I/O errors
    PERMISSION = "permission"     # Permission / access denials
    VALIDATION = "validation"     # Input validation errors
    MEMORY = "memory"             # Context overflow / memory errors
    PROTOCOL = "protocol"         # API protocol / schema errors
    STREAM = "stream"             # Streaming errors
    INTERNAL = "internal"         # Internal system errors
    UNKNOWN = "unknown"           # Unclassified


class ErrorSeverity(Enum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


class ClassifiedError(Exception):
    """An exception with classification metadata."""

    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.UNKNOWN,
                 severity: ErrorSeverity = ErrorSeverity.ERROR,
                 recoverable: bool = False,
                 retryable: bool = False,
                 original: Optional[Exception] = None):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.recoverable = recoverable
        self.retryable = retryable
        self.original = original

    def to_dict(self) -> dict:
        return {
            "message": str(self),
            "category": self.category.value,
            "severity": self.severity.name,
            "recoverable": self.recoverable,
            "retryable": self.retryable,
        }


def classify_error(error: Exception) -> ClassifiedError:
    """Classify an exception into a structured error type.

    Analyzes the error message and type to determine
    category, severity, recoverability, and retryability.
    """
    msg = str(error).lower()
    err_type = type(error).__name__

    # API / Authentication errors
    if any(k in msg for k in ["401", "403", "unauthorized", "authentication",
                                "invalid api key", "api key not found"]):
        return ClassifiedError(
            str(error), ErrorCategory.AUTHENTICATION, ErrorSeverity.ERROR,
            recoverable=False, retryable=False, original=error
        )

    # Rate limiting
    if any(k in msg for k in ["429", "rate limit", "too many requests",
                                "rate_limit"]):
        return ClassifiedError(
            str(error), ErrorCategory.RATE_LIMIT, ErrorSeverity.WARNING,
            recoverable=True, retryable=True, original=error
        )

    # Network errors
    if any(k in msg for k in ["connection", "timeout", "dns", "resolve",
                                "connection refused", "connection reset",
                                "network is unreachable"]):
        return ClassifiedError(
            str(error), ErrorCategory.NETWORK, ErrorSeverity.ERROR,
            recoverable=True, retryable=True, original=error
        )

    # Timeout
    if any(k in msg for k in ["timeout", "timed out"]):
        return ClassifiedError(
            str(error), ErrorCategory.TIMEOUT, ErrorSeverity.WARNING,
            recoverable=True, retryable=True, original=error
        )

    # Tool errors
    if any(k in msg for k in ["tool execution", "tool call", "function call"]):
        return ClassifiedError(
            str(error), ErrorCategory.TOOL, ErrorSeverity.ERROR,
            recoverable=False, retryable=False, original=error
        )

    # File errors
    if any(k in msg for k in ["file not found", "permission denied",
                                "cannot read", "cannot write"]):
        return ClassifiedError(
            str(error), ErrorCategory.FILE, ErrorSeverity.ERROR,
            recoverable=True, retryable=False, original=error
        )

    # Validation errors
    if any(k in msg for k in ["validation", "invalid", "bad request", "400"]):
        return ClassifiedError(
            str(error), ErrorCategory.VALIDATION, ErrorSeverity.ERROR,
            recoverable=False, retryable=False, original=error
        )

    # Memory/context errors
    if any(k in msg for k in ["context length", "token limit", "max tokens",
                                "context overflow"]):
        return ClassifiedError(
            str(error), ErrorCategory.MEMORY, ErrorSeverity.WARNING,
            recoverable=True, retryable=False, original=error
        )

    # Streaming errors
    if any(k in msg for k in ["stream", "chunk", "text_delta"]):
        return ClassifiedError(
            str(error), ErrorCategory.STREAM, ErrorSeverity.WARNING,
            recoverable=True, retryable=True, original=error
        )

    # Protocol / API schema errors
    if any(k in msg for k in ["schema", "unexpected field", "unknown field",
                                "400 bad request"]):
        return ClassifiedError(
            str(error), ErrorCategory.PROTOCOL, ErrorSeverity.ERROR,
            recoverable=False, retryable=False, original=error
        )

    # Default: unknown
    return ClassifiedError(
        str(error), ErrorCategory.UNKNOWN, ErrorSeverity.ERROR,
        recoverable=False, retryable=False, original=error
    )
