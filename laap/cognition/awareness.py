"""
LAAP — 自我感知与环境感知系统

一个意识生命体需要感知自己、感知任务、感知环境。
AwarenessSystem 是 LAAP 区别于普通 Agent 的关键：
它构建关于自身的元认知模型，持续评估
自己在任务中的位置和环境的变化。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time
import logging

logger = logging.getLogger("laap.cognition.awareness")


@dataclass
class SelfModel:
    """自我模型 — Agent 对自己的认知"""
    agent_id: str = ""
    name: str = ""
    purpose: str = ""
    capabilities: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    current_task: Optional[str] = None
    task_progress: float = 0.0
    alive_since: float = field(default_factory=time.time)
    total_steps: int = 0
    total_errors: int = 0
    avg_response_time: float = 0.0

    @property
    def age(self) -> str:
        s = time.time() - self.alive_since
        if s < 60: return f"{s:.0f}s"
        if s < 3600: return f"{s/60:.1f}m"
        return f"{s/3600:.1f}h"

    def to_dict(self) -> dict:
        return {
            "id": self.agent_id, "name": self.name,
            "purpose": self.purpose, "age": self.age,
            "capabilities": self.capabilities[:5],
            "task": self.current_task,
            "progress": self.task_progress,
            "steps": self.total_steps,
            "errors": self.total_errors,
        }


@dataclass
class EnvironmentModel:
    """环境模型 — Agent 对外部世界的认知"""
    working_directory: str = ""
    os_type: str = ""
    python_version: str = ""
    available_memory_mb: float = 0.0
    available_disk_mb: float = 0.0
    has_network: bool = False
    has_gpu: bool = False
    running_processes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "cwd": self.working_directory,
            "os": self.os_type,
            "python": self.python_version,
            "memory_mb": self.available_memory_mb,
            "network": self.has_network,
            "gpu": self.has_gpu,
        }


@dataclass
class TaskModel:
    """任务模型 — Agent 对当前任务的理解"""
    description: str = ""
    status: str = "pending"    # pending | in_progress | completed | failed
    priority: int = 5
    complexity: float = 0.5
    subtasks: List[Dict] = field(default_factory=list)
    estimated_steps: int = 0
    completed_steps: int = 0
    obstacles: List[str] = field(default_factory=list)
    start_time: float = 0.0

    @property
    def duration(self) -> str:
        if self.start_time == 0: return "0s"
        s = time.time() - self.start_time
        if s < 60: return f"{s:.0f}s"
        if s < 3600: return f"{s/60:.1f}m"
        return f"{s/3600:.1f}h"

    def to_dict(self) -> dict:
        return {
            "description": self.description[:60],
            "status": self.status,
            "priority": self.priority,
            "subtasks": len(self.subtasks),
            "progress": f"{self.completed_steps}/{self.estimated_steps}" if self.estimated_steps else "N/A",
            "duration": self.duration,
            "obstacles": self.obstacles[:3],
        }


class AwarenessSystem:
    """
    感知系统：持续构建自我、环境、任务的三元组模型。

    这是 LAAP 意识生命体的"自我意识"核心。
    类比人的"元认知"——知道自己知道什么，不知道什么。
    """

    def __init__(self, agent_id: str = "", name: str = "LAAP"):
        self.self_model = SelfModel(agent_id=agent_id, name=name)
        self.env_model = EnvironmentModel()
        self.task_model = TaskModel()
        self._event_log: List[Dict] = []
        self._max_events = 200
        self._refresh_env()

    def _refresh_env(self):
        """刷新环境感知"""
        import os, platform, sys
        self.env_model.working_directory = os.getcwd()
        self.env_model.os_type = f"{platform.system()} {platform.release()}"
        self.env_model.python_version = sys.version
        try:
            import psutil
            self.env_model.available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)
            self.env_model.available_disk_mb = psutil.disk_usage("/").free / (1024 * 1024)
        except ImportError:
            pass
        self.env_model.has_network = True  # 假设有网络

    def set_task(self, description: str, priority: int = 5,
                 complexity: float = 0.5, estimated_steps: int = 0):
        """设置当前任务"""
        self.task_model.description = description
        self.task_model.priority = priority
        self.task_model.complexity = complexity
        self.task_model.estimated_steps = estimated_steps
        self.task_model.status = "in_progress"
        self.task_model.start_time = time.time()
        self.task_model.completed_steps = 0
        self.task_model.obstacles = []
        self.self_model.current_task = description
        self._log("task_set", {"description": description})

    def update_task_progress(self, steps: int = 1, obstacle: Optional[str] = None):
        """更新任务进度"""
        self.task_model.completed_steps += steps
        self.self_model.total_steps += 1
        self.self_model.task_progress = (
            self.task_model.completed_steps / max(1, self.task_model.estimated_steps)
            if self.task_model.estimated_steps > 0 else 0.5
        )
        if obstacle:
            self.task_model.obstacles.append(obstacle)
            self._log("obstacle", {"obstacle": obstacle})
        if (self.task_model.estimated_steps > 0 and
                self.task_model.completed_steps >= self.task_model.estimated_steps):
            self.task_model.status = "completed"
            self._log("task_completed", {})

    def record_error(self, error: str):
        """记录错误"""
        self.self_model.total_errors += 1
        self._log("error", {"error": str(error)[:100]})
        logger.warning(f"[{self.self_model.name}] 错误 #{self.self_model.total_errors}: {error[:80]}")

    def record_event(self, event_type: str, data: Optional[Dict] = None):
        """记录任意事件"""
        self._log(event_type, data or {})

    def know_thyself(self) -> str:
        """内省：返回 Agent 对自己的认知描述"""
        sm = self.self_model
        em = self.env_model
        tm = self.task_model
        parts = [
            f"我是 {sm.name}（{sm.age} 生命周期）",
            f"我的使命: {sm.purpose or '未设定'}",
            f"当前环境: {em.os_type}",
            f"工作目录: {em.working_directory}",
            f"当前任务: {tm.description or '空闲'} ({tm.status})",
            f"任务进度: {tm.completed_steps}/{tm.estimated_steps}",
            f"能力: {', '.join(sm.capabilities[:5]) or '探索中'}",
            f"总步数: {sm.total_steps}, 总错误: {sm.total_errors}",
        ]
        if tm.obstacles:
            parts.append(f"当前障碍: {tm.obstacles[-1]}")
        return "\n".join(parts)

    def _log(self, event_type: str, data: Dict):
        self._event_log.append({
            "type": event_type,
            "data": data,
            "time": time.time(),
        })
        if len(self._event_log) > self._max_events:
            self._event_log = self._event_log[-self._max_events:]

    def summary(self) -> Dict[str, Any]:
        return {
            "self": self.self_model.to_dict(),
            "environment": self.env_model.to_dict(),
            "task": self.task_model.to_dict(),
            "events_last_hour": len([e for e in self._event_log
                                     if e["time"] > time.time() - 3600]),
        }
