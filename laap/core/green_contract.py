"""
LAAP — Green Contract System

Function-level contracts (preconditions, postconditions, invariants).
Inspired by claw-code's green_contract pattern for error resilience.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic
import logging, traceback
from functools import wraps

logger = logging.getLogger("laap.core.green_contract")

T = TypeVar("T")


class ContractError(Exception):
    """Raised when a contract is violated."""
    pass


@dataclass
class Contract:
    """A contract that can be applied to functions."""
    name: str
    description: str = ""
    preconditions: List[Callable] = None
    postconditions: List[Callable] = None
    invariants: List[Callable] = None

    def check_pre(self, *args, **kwargs):
        if self.preconditions:
            for cond in self.preconditions:
                if not cond(*args, **kwargs):
                    raise ContractError(
                        f"Precondition failed for {self.name}: {cond.__doc__ or cond.__name__}"
                    )

    def check_post(self, result: Any, *args, **kwargs):
        if self.postconditions:
            for cond in self.postconditions:
                if not cond(result, *args, **kwargs):
                    raise ContractError(
                        f"Postcondition failed for {self.name}: {cond.__doc__ or cond.__name__}"
                    )


class ErrorChain:
    """Error chain with context propagation. Tracks root cause path."""

    def __init__(self, message: str, cause: Optional[Exception] = None,
                 context: Optional[Dict] = None):
        self.message = message
        self.cause = cause
        self.context = context or {}
        self.timestamp = __import__("time").time()
        self.traceback = "".join(
            traceback.format_exception(type(cause), cause, cause.__traceback__)
        ) if cause else ""

    @property
    def root_cause(self) -> str:
        if self.cause:
            if hasattr(self.cause, "__cause__") and self.cause.__cause__:
                return ErrorChain(
                    str(self.cause.__cause__),
                    cause=self.cause.__cause__,
                ).root_cause
            return str(self.cause)
        return self.message

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "root_cause": self.root_cause,
            "cause": str(self.cause) if self.cause else None,
            "context": self.context,
            "traceback": self.traceback[:500] if self.traceback else None,
        }

    def __str__(self) -> str:
        parts = [f"Error: {self.message}"]
        if self.cause:
            parts.append(f"  Caused by: {self.cause}")
        return "\n".join(parts)


def with_contract(name: str = "", preconditions: List[Callable] = None,
                  postconditions: List[Callable] = None):
    """Decorator to apply contracts to a function."""
    def decorator(func: Callable) -> Callable:
        contract = Contract(
            name=name or func.__name__,
            description=func.__doc__ or "",
            preconditions=preconditions,
            postconditions=postconditions,
        )

        @wraps(func)
        def wrapper(*args, **kwargs):
            contract.check_pre(*args, **kwargs)
            result = func(*args, **kwargs)
            contract.check_post(result, *args, **kwargs)
            return result

        return wrapper
    return decorator


def safe_execute(func: Callable, *args, default_return: Any = None,
                 context: Optional[Dict] = None, **kwargs) -> Any:
    """Execute a function with error chain tracking."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Safe execute failed: {e}", exc_info=True)
        error = ErrorChain(
            message=f"Failed to execute {func.__name__}",
            cause=e,
            context=context,
        )
        raise ContractError(str(error)) from e
