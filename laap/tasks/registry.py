"""
LAAP — Task Registry

Background task management with scheduling, execution, and monitoring.
"""

from __future__ import annotations
import logging, time, uuid, threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

logger = logging.getLogger("laap.tasks")


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Task:
    """A single task"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    handler: Optional[Callable] = None
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    timeout: int = 300
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def is_ready(self) -> bool:
        return self.status == TaskStatus.PENDING

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name,
            "priority": self.priority.name,
            "status": self.status.value,
            "duration": self.duration,
            "error": self.error[:100] if self.error else None,
            "dependencies": self.dependencies,
        }


class TaskRegistry:
    """Central task registry and executor"""

    def __init__(self, max_workers: int = 4):
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()
        self._workers = max_workers
        self._running: Dict[str, threading.Thread] = {}

    def register(self, task: Task) -> str:
        with self._lock:
            self._tasks[task.id] = task
        logger.debug(f"Task registered: {task.name} ({task.id})")
        return task.id

    def submit(self, name: str, handler: Callable, *args,
               priority: TaskPriority = TaskPriority.NORMAL,
               timeout: int = 300, **kwargs) -> str:
        task = Task(
            name=name, handler=handler,
            args=args, kwargs=kwargs,
            priority=priority, timeout=timeout,
        )
        return self.register(task)

    def execute(self, task_id: str) -> Any:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")

            # Check dependencies
            for dep_id in task.dependencies:
                dep = self._tasks.get(dep_id)
                if dep and dep.status != TaskStatus.COMPLETED:
                    return None  # Not ready yet

            if task.status != TaskStatus.PENDING:
                return task.result
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()

        try:
            result = task.handler(*task.args, **task.kwargs)
            with self._lock:
                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
            return result
        except Exception as e:
            with self._lock:
                task.error = str(e)
                task.status = TaskStatus.FAILED
                task.completed_at = time.time()
            logger.error(f"Task {task.name} failed: {e}")
            return None

    def execute_async(self, task_id: str) -> bool:
        """Execute a task in a background thread."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status != TaskStatus.PENDING:
                return False
            task.status = TaskStatus.RUNNING

        thread = threading.Thread(
            target=self._run_async, args=(task_id,),
            daemon=True,
        )
        with self._lock:
            self._running[task_id] = thread
        thread.start()
        return True

    def _run_async(self, task_id: str):
        try:
            self.execute(task_id)
        finally:
            with self._lock:
                self._running.pop(task_id, None)

    def get(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                return False
            task.status = TaskStatus.CANCELLED
            return True

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        with self._lock:
            tasks = list(self._tasks.values())
            if status:
                tasks = [t for t in tasks if t.status == status]
            return sorted(tasks, key=lambda t: t.priority.value, reverse=True)

    @property
    def status(self) -> dict:
        with self._lock:
            counts = {}
            for t in self._tasks.values():
                counts[t.status.value] = counts.get(t.status.value, 0) + 1
            return {
                "total": len(self._tasks),
                "running": len(self._running),
                "by_status": counts,
            }


registry = TaskRegistry()
