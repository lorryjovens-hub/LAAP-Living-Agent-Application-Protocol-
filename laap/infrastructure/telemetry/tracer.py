"""Distributed Tracing — OpenTelemetry compatible"""
from __future__ import annotations
import time, uuid, json, logging, threading
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("infrastructure.telemetry.tracer")

_current_span: ContextVar = ContextVar("current_span", default=None)

@dataclass
class Span:
    trace_id: str = ""
    span_id: str = ""
    parent_id: Optional[str] = None
    name: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: Dict = field(default_factory=dict)
    status: str = "ok"

class Tracer:
    def __init__(self, service_name: str = "laap"):
        self.service_name = service_name
        self._spans: List[Span] = []
        self._lock = threading.RLock()
    def start_span(self, name: str, attributes: Dict = None) -> Span:
        trace_id = uuid.uuid4().hex[:16]
        parent = _current_span.get()
        span = Span(trace_id=trace_id, span_id=uuid.uuid4().hex[:12],
                   parent_id=parent.span_id if parent else None,
                   name=name, attributes=attributes or {})
        _current_span.set(span)
        return span
    def end_span(self, span: Span, status: str = "ok"):
        span.end_time = time.time()
        span.status = status
        with self._lock:
            self._spans.append(span)
        _current_span.set(None)
    def trace(self, name: str, attributes: Dict = None):
        def decorator(func):
            def wrapper(*args, **kwargs):
                span = self.start_span(name, attributes)
                try:
                    result = func(*args, **kwargs)
                    self.end_span(span, "ok")
                    return result
                except Exception as e:
                    self.end_span(span, f"error: {e}")
                    raise
            return wrapper
        return decorator
    def get_spans(self, limit: int = 100) -> List[Span]:
        with self._lock:
            return self._spans[-limit:]
