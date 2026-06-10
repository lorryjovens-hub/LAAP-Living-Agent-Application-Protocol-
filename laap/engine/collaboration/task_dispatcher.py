"""Task Dispatcher — 任务分发与调度"""
from __future__ import annotations
import time, uuid, logging, threading
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("engine.collaboration.dispatcher")

class SchedulingStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_BUSY = "least_busy"
    WEIGHTED = "weighted"
    PREDICTIVE = "predictive"

@dataclass
class Worker:
    id: str = ""
    name: str = ""
    capacity: int = 5
    current_load: int = 0
    weight: float = 1.0
    last_heartbeat: float = field(default_factory=time.time)
    skills: List[str] = field(default_factory=list)

@dataclass
class Task:
    id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    name: str = ""
    payload: Any = None
    priority: int = 0
    deadline: float = 0.0
    assigned_to: str = ""
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    result: Any = None

class TaskDispatcher:
    def __init__(self, strategy: SchedulingStrategy = SchedulingStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self._workers: Dict[str, Worker] = {}
        self._tasks: Dict[str, Task] = {}
        self._queue: List[Task] = []
        self._lock = threading.RLock()
        self._rr_index = 0
    def register_worker(self, worker_id: str, name: str, capacity: int = 5, skills: List[str] = None):
        with self._lock:
            self._workers[worker_id] = Worker(id=worker_id, name=name, capacity=capacity, skills=skills or [])
    def unregister_worker(self, worker_id: str):
        with self._lock:
            self._workers.pop(worker_id, None)
    def submit(self, task: Task) -> str:
        with self._lock:
            self._tasks[task.id] = task
            self._queue.append(task)
        return task.id
    def dispatch(self) -> Optional[str]:
        if not self._queue:
            return None
        task = self._queue.pop(0)
        worker = self._select_worker(task)
        if worker:
            with self._lock:
                task.assigned_to = worker.id
                task.status = "dispatched"
                worker.current_load += 1
            logger.info(f"Task {task.id} dispatched to {worker.name}")
            return worker.id
        self._queue.insert(0, task)
        return None
    def _select_worker(self, task: Task) -> Optional[Worker]:
        available = [w for w in self._workers.values() if w.current_load < w.capacity]
        if not available:
            return None
        if self.strategy == SchedulingStrategy.ROUND_ROBIN:
            self._rr_index = (self._rr_index + 1) % len(available)
            return available[self._rr_index]
        elif self.strategy == SchedulingStrategy.LEAST_BUSY:
            return min(available, key=lambda w: w.current_load)
        elif self.strategy == SchedulingStrategy.WEIGHTED:
            return max(available, key=lambda w: w.weight * (1 - w.current_load / w.capacity))
        return available[0]
    def complete(self, task_id: str, result: Any = None):
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = "completed"
                task.result = result
                if task.assigned_to in self._workers:
                    self._workers[task.assigned_to].current_load = max(0, self._workers[task.assigned_to].current_load - 1)
    def get_stats(self) -> dict:
        return {"workers": len(self._workers), "pending": len(self._queue), "total": len(self._tasks)}
