"""LAAP - Workflow Engine"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import uuid, time, logging

logger = logging.getLogger("laap.workflow")


class WorkflowStatus(Enum):
    PENDING = "pending"; RUNNING = "running"
    COMPLETED = "completed"; FAILED = "failed"


@dataclass
class WorkflowStep:
    name: str; handler: Callable
    args: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    result: Any = None; error: Optional[str] = None
    start_time: float = 0.0; end_time: float = 0.0

    @property
    def duration(self) -> float:
        if self.end_time > 0: return self.end_time - self.start_time
        return time.time() - self.start_time if self.start_time > 0 else 0.0


class Workflow:
    def __init__(self, name: str = "Workflow"):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.steps: Dict[str, WorkflowStep] = {}
        self.status = WorkflowStatus.PENDING
        self._results: Dict[str, Any] = {}
        self._order: List[str] = []

    def add_step(self, name: str, handler: Callable,
                 depends_on: Optional[List[str]] = None,
                 **kwargs):
        step = WorkflowStep(name=name, handler=handler, args=kwargs,
                            depends_on=depends_on or [])
        self.steps[name] = step
        self._order.append(name)
        return self

    def run(self) -> dict:
        self.status = WorkflowStatus.RUNNING
        logger.info(f"Workflow [{self.name}] ���� ({len(self.steps)} steps)")
        start = time.time()

        for name in self._order:
            step = self.steps[name]
            deps_met = all(d in self._results for d in step.depends_on)
            if not deps_met:
                step.status = WorkflowStatus.FAILED
                step.error = f"����δ����: {step.depends_on}"
                continue
            step.start_time = time.time()
            step.status = WorkflowStatus.RUNNING
            try:
                merged_args = {**step.args}
                for dep in step.depends_on:
                    merged_args[f"_{dep}_result"] = self._results[dep]
                step.result = step.handler(**merged_args)
                step.status = WorkflowStatus.COMPLETED
                self._results[name] = step.result
                logger.info(f"  Step [{name}] OK ({step.duration:.2f}s)")
            except Exception as e:
                step.status = WorkflowStatus.FAILED
                step.error = str(e)
                logger.error(f"  Step [{name}] FAILED: {e}")
            step.end_time = time.time()

        self.status = WorkflowStatus.COMPLETED
        total = time.time() - start
        failed = [s for s in self.steps.values() if s.status == WorkflowStatus.FAILED]
        logger.info(f"Workflow done: {total:.1f}s, {len(failed)} failed")
        return {"workflow": self.name, "status": self.status.value,
                "duration_s": round(total, 2), "failed": len(failed),
                "results": {n: str(r)[:100] for n, r in self._results.items()}}

    def status_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "status": self.status.value,
                "steps": [{"name": s.name, "status": s.status.value,
                           "duration": round(s.duration, 2)}
                          for s in self.steps.values()]}
