"""
LAAP — Task Execution Manager
Tracks task lifecycle (pending → running → completed/failed).
Provides real-time status for the TUI sidebar.
"""

from __future__ import annotations
import time, threading
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Task:
    id: str
    name: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    parent_id: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    error: Optional[str] = None
    result: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        if self.started_at:
            return time.time() - self.started_at
        return None


_task_id_counter = 0


def _next_task_id() -> str:
    global _task_id_counter
    _task_id_counter += 1
    return f"t{_task_id_counter}"


class TaskManager:
    """Manages task lifecycle with thread-safe operations."""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._root_tasks: List[str] = []
        self._lock = threading.Lock()

    def add_task(self, name: str, description: str = "",
                 parent_id: Optional[str] = None) -> Task:
        tid = _next_task_id()
        task = Task(id=tid, name=name, description=description,
                    parent_id=parent_id)
        with self._lock:
            self._tasks[tid] = task
            if parent_id:
                parent = self._tasks.get(parent_id)
                if parent:
                    parent.subtasks.append(tid)
            else:
                self._root_tasks.append(tid)
        return task

    def start_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
        return True

    def complete_task(self, task_id: str, result: str = "") -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            task.result = result
        return True

    def fail_task(self, task_id: str, error: str = "") -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            task.error = error
        return True

    def skip_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            task.status = TaskStatus.SKIPPED
            task.completed_at = time.time()
        return True

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def get_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        with self._lock:
            tasks = [self._tasks[tid] for tid in self._root_tasks if tid in self._tasks]
            if status:
                tasks = [t for t in tasks if t.status == status]
            return list(tasks)

    def get_all_tasks(self) -> List[Task]:
        with self._lock:
            return list(self._tasks.values())

    def count(self, status: Optional[TaskStatus] = None) -> int:
        with self._lock:
            if status is None:
                return len(self._tasks)
            return sum(1 for t in self._tasks.values() if t.status == status)

    def summary(self) -> Dict[str, int]:
        with self._lock:
            counts = {s.value: 0 for s in TaskStatus}
            for t in self._tasks.values():
                counts[t.status.value] = counts.get(t.status.value, 0) + 1
            return counts

    def clear_completed(self):
        with self._lock:
            done = {s.value for s in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED]}
            self._tasks = {tid: t for tid, t in self._tasks.items()
                          if t.status.value not in done}
            self._root_tasks = [tid for tid in self._root_tasks if tid in self._tasks]

    def auto_track(self, name: str, description: str = "",
                   parent_id: Optional[str] = None) -> str:
        """Create and auto-start a task. Returns task_id."""
        task = self.add_task(name, description, parent_id)
        self.start_task(task.id)
        return task.id

    def get_tree(self) -> List[Dict]:
        """Return task tree as nested dicts for TUI rendering."""
        def _build(tid: str) -> Dict:
            task = self._tasks.get(tid)
            if not task:
                return {}
            return {
                "id": task.id,
                "name": task.name,
                "status": task.status.value,
                "description": task.description,
                "duration": task.duration,
                "error": task.error,
                "children": [_build(stid) for stid in task.subtasks if stid in self._tasks],
            }
        with self._lock:
            return [_build(tid) for tid in self._root_tasks if tid in self._tasks]
