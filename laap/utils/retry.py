"""
LAAP — Retry Utilities (ported from Hermes Agent)

Jittered exponential backoff for transient failures
"""

from __future__ import annotations
import random
import time
import logging
from functools import wraps
from typing import Any, Callable, Optional, Type, Tuple

logger = logging.getLogger("laap.utils.retry")


def jittered_backoff(attempt: int, base_delay: float = 1.0,
                     max_delay: float = 60.0, jitter: float = 0.1) -> float:
    """Calculate delay with exponential backoff and jitter.

    Args:
        attempt: Attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Jitter factor (0.0 = no jitter, 0.1 = 10%)

    Returns:
        Delay in seconds
    """
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter_amount = delay * jitter * random.random()
    return delay + jitter_amount


def retry(max_attempts: int = 3, base_delay: float = 1.0,
          max_delay: float = 60.0, jitter: float = 0.1,
          exceptions: Tuple[Type[Exception], ...] = (Exception,),
          on_retry: Optional[Callable] = None):
    """Decorator: retry a function with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts
        base_delay: Base delay between retries
        max_delay: Maximum delay cap
        jitter: Jitter factor
        exceptions: Exception types that trigger retry
        on_retry: Callback fn(attempt, exception) called before each retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts - 1:
                        delay = jittered_backoff(attempt, base_delay, max_delay, jitter)
                        if on_retry:
                            on_retry(attempt + 1, e)
                        logger.warning(
                            f"Retry {attempt + 1}/{max_attempts} for {func.__name__}: {e}"
                        )
                        time.sleep(delay)
            raise last_exc  # type: ignore
        return wrapper
    return decorator


class RetryHandler:
    """Stateful retry handler with configurable strategy."""

    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0,
                 max_delay: float = 60.0, jitter: float = 0.1):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.attempt = 0
        self.last_error: Optional[Exception] = None

    def reset(self):
        """Reset attempt counter."""
        self.attempt = 0
        self.last_error = None

    def should_retry(self) -> bool:
        """Check if we should retry after a failure."""
        return self.attempt < self.max_attempts

    def record_failure(self, error: Exception):
        """Record a failure and return delay before next attempt."""
        self.attempt += 1
        self.last_error = error
        return jittered_backoff(self.attempt - 1, self.base_delay,
                                self.max_delay, self.jitter)

    def wait_before_retry(self):
        """Wait appropriate delay before next retry."""
        delay = self.record_failure(self.last_error)
        if self.should_retry():
            time.sleep(delay)
