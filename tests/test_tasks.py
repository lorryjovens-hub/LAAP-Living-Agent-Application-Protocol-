"""Tests for LAAP Task Registry"""
import pytest
from laap.tasks.registry import TaskRegistry, Task, TaskStatus, TaskPriority


class TestTaskRegistry:
    def test_register_and_get(self):
        registry = TaskRegistry()
        task_id = registry.submit("test_task", lambda x: x, "hello")
        task = registry.get(task_id)
        assert task is not None
        assert task.name == "test_task"

    def test_execute(self):
        registry = TaskRegistry()
        task_id = registry.submit("echo", lambda msg: f"Echo: {msg}", "test")
        result = registry.execute(task_id)
        assert result == "Echo: test"
        task = registry.get(task_id)
        assert task.status == TaskStatus.COMPLETED

    def test_execute_failure(self):
        registry = TaskRegistry()

        def failing():
            raise ValueError("Intentional failure")

        task_id = registry.submit("fail", failing)
        result = registry.execute(task_id)
        assert result is None
        task = registry.get(task_id)
        assert task.status == TaskStatus.FAILED

    def test_cancel(self):
        registry = TaskRegistry()
        task_id = registry.submit("cancellable", lambda: None)
        assert registry.cancel(task_id)
        task = registry.get(task_id)
        assert task.status == TaskStatus.CANCELLED

    def test_list_by_status(self):
        registry = TaskRegistry()
        t1 = registry.submit("task1", lambda: None)
        registry.execute(t1)
        pending = registry.list_tasks(TaskStatus.PENDING)
        completed = registry.list_tasks(TaskStatus.COMPLETED)
        assert len(completed) >= 1

    def test_priority_order(self):
        registry = TaskRegistry()
        low = registry.submit("low", lambda: None, priority=TaskPriority.LOW)
        high = registry.submit("high", lambda: None, priority=TaskPriority.HIGH)
        all_tasks = registry.list_tasks()
        assert all_tasks[0].priority == TaskPriority.HIGH

    def test_status_counts(self):
        registry = TaskRegistry()
        status = registry.status
        assert "total" in status
        assert "by_status" in status
