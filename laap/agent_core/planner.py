"""
LAAP Planner — 智能体任务规划与分解
支持 ReAct / Plan-and-Solve / Tree-of-Thought
"""
from __future__ import annotations
import time, json, logging, uuid, re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("agent_core.planner")

class PlanningStrategy(str, Enum):
    REACT = "react"
    PLAN_SOLVE = "plan_solve"
    TOT = "tree_of_thought"
    STRAIGHT = "straight"

@dataclass
class Task:
    id: str = ""
    description: str = ""
    status: str = "pending"
    subtasks: List["Task"] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    result: Any = None
    assigned_tool: str = ""
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        return {"id": self.id, "description": self.description[:60],
                "status": self.status, "subtasks": len(self.subtasks),
                "result": str(self.result)[:100] if self.result else None}

@dataclass
class Plan:
    id: str = ""
    goal: str = ""
    tasks: List[Task] = field(default_factory=list)
    strategy: PlanningStrategy = PlanningStrategy.REACT
    created_at: float = field(default_factory=time.time)
    completed: bool = False
    summary: str = ""

class Planner:
    """任务规划器 — 将目标分解为可执行步骤"""
    
    def __init__(self, strategy: PlanningStrategy = PlanningStrategy.REACT):
        self.strategy = strategy
        self._history: List[Plan] = []
    
    def plan(self, goal: str, available_tools: List[str] = None) -> Plan:
        tasks = self._decompose(goal, available_tools or [])
        plan = Plan(
            id=f"plan_{uuid.uuid4().hex[:8]}",
            goal=goal,
            tasks=tasks,
            strategy=self.strategy,
        )
        self._history.append(plan)
        return plan
    
    def _decompose(self, goal: str, tools: List[str]) -> List[Task]:
        """将目标分解为子任务"""
        tasks = []
        
        # 分析目标，分解为步骤
        steps = self._analyze_goal(goal)
        
        for i, step in enumerate(steps):
            task = Task(
                id=f"task_{uuid.uuid4().hex[:6]}",
                description=step,
                status="pending",
            )
            if i > 0:
                task.dependencies.append(tasks[i-1].id)
            tasks.append(task)
        
        # 如果没有自动分解出步骤，创建一个通用任务
        if not tasks:
            tasks.append(Task(id=f"task_{uuid.uuid4().hex[:6]}", 
                            description=goal, status="pending"))
        
        return tasks
    
    def _analyze_goal(self, goal: str) -> List[str]:
        """分析目标语义，提取步骤"""
        goal_lower = goal.lower()
        
        # 识别常见模式
        patterns = {
            r"(?:分析|分析一下|analyze)\s+(.+?)(?:。|$|请)": ["收集数据", f"分析{goal[:20]}", "总结结果"],
            r"(?:搜索|查找|search|find)\s+(.+?)(?:。|$|请)": [f"搜索相关信息", "整理结果"],
            r"(?:总结|总结一下|summarize)\s+(.+?)(?:。|$|请)": ["理解内容", "提取关键信息", "生成摘要"],
            r"(?:写|编写|写一个|create|write)\s+(.+?)(?:。|$|请)": ["确定需求", "设计方案", "实现代码", "测试验证"],
        }
        
        for pattern, steps in patterns.items():
            if re.search(pattern, goal_lower):
                return steps
        
        return [f"理解需求: {goal[:50]}", "分析并处理", "返回结果"]
    
    def get_next_task(self, plan: Plan) -> Optional[Task]:
        for task in plan.tasks:
            if task.status == "pending":
                deps_met = all(
                    any(t.id == dep and t.status == "completed" for t in plan.tasks)
                    for dep in task.dependencies
                )
                if deps_met:
                    return task
        return None
    
    def update_task(self, plan: Plan, task_id: str, status: str, result: Any = None):
        for task in plan.tasks:
            if task.id == task_id:
                task.status = status
                task.result = result
                break
        plan.completed = all(t.status == "completed" for t in plan.tasks)
    
    def summarize_plan(self, plan: Plan) -> str:
        lines = [f"📋 计划: {plan.goal[:50]}"]
        for t in plan.tasks:
            icon = "✅" if t.status == "completed" else "⏳" if t.status == "in_progress" else "⬜"
            lines.append(f"  {icon} {t.description[:50]}")
        return "\n".join(lines)
    
    def get_stats(self) -> dict:
        return {"total_plans": len(self._history), "strategy": self.strategy.value}
