"""
LAAP — Swarm 多 Agent 编排

支持三种协作模式：
  - Route: 路由到最合适的 Agent
  - Collaborate: 多个 Agent 协作完成
  - Coordinate: 有管理者的协调模式
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import logging

from laap.agent.base import Agent
from laap.orchestration.shared_state import SharedStateBus
from laap.orchestration.protocol import MessageRouter, AgentMessage, MessageType

logger = logging.getLogger("laap.orchestration.swarm")


class SwarmMode:
    ROUTE = "route"
    COLLABORATE = "collaborate"
    COORDINATE = "coordinate"


@dataclass
class SwarmTask:
    id: str
    description: str
    assigned_to: Optional[str] = None
    status: str = "pending"
    result: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


class Swarm:
    """多 Agent 编排系统"""

    def __init__(self, name: str = "LAAP-Swarm",
                 mode: str = SwarmMode.ROUTE):
        self.name = name
        self.mode = mode
        self.agents: Dict[str, Agent] = {}
        self.router = MessageRouter()
        self.state_bus = SharedStateBus()
        self.tasks: List[SwarmTask] = []
        self.logger = logging.getLogger("laap.orchestration.swarm")

    def add_agent(self, name: str, agent: Agent,
                  description: str = ""):
        self.agents[name] = agent
        self.state_bus.register(agent.id, name)
        self.logger.info(f"Swarm 添加 Agent [{name}]: {agent.id[:8]}")

    def remove_agent(self, name: str):
        if name in self.agents:
            del self.agents[name]

    def route(self, task: str, context: Optional[Dict] = None) -> str:
        """路由模式：选择最合适的 Agent"""
        if not self.agents:
            return "Swarm 中没有 Agent"

        scores = {}
        for name, agent in self.agents.items():
            if not agent.alive:
                continue
            # 基于 Agent 状态的简单评分
            if hasattr(agent, 'emotion_gradient'):
                conf = agent.emotion_gradient.state.confidence
                comp = agent.needs.needs.get(
                    list(agent.needs.needs.keys())[1],
                    type('o', (), {'current_level': 0.5})(),
                ).current_level
                scores[name] = conf * 0.6 + comp * 0.4
            else:
                scores[name] = 0.5

        if not scores:
            return "没有可用的 Agent"

        best = max(scores, key=scores.get)
        self.logger.info(f"Route: {best} <- {task[:40]}")

        result = self.agents[best].run(task)
        self.state_bus.publish(self.agents[best].id,
                               {"last_task": task[:40], "result": str(result)[:100]})
        return f"[{best}]: {result}"

    def collaborate(self, task: str, assign_to: Optional[List[str]] = None) -> str:
        """协作模式：多 Agent 分工"""
        targets = assign_to or list(self.agents.keys())
        results = []
        for name in targets:
            if name in self.agents and self.agents[name].alive:
                r = self.agents[name].run(f"{task} (part for {name})")
                results.append(f"[{name}]: {r[:200]}")
                self.state_bus.publish(self.agents[name].id,
                                       {"task": task[:40], "result": str(r)[:100]})
        return "\n".join(results)

    def coordinate(self, task: str, manager: str) -> str:
        """协调模式：管理者分配子任务"""
        if manager not in self.agents:
            return f"管理者 {manager} 不存在"

        # 管理者分解任务
        subtask_prompt = (
            f"将以下任务分解为子任务并分配给合适的团队成员。"
            f"可用成员: {', '.join(self.agents.keys())}\n任务: {task}"
        )
        plan = self.agents[manager].run(subtask_prompt)

        # 收集结果
        results = []
        for name in self.agents:
            if name != manager and self.agents[name].alive:
                r = self.agents[name].run(f"{task} (from {manager})")
                results.append(f"[{name}]: {r[:200]}")
                self.state_bus.publish(self.agents[name].id,
                                       {"task": task[:40], "coordinated": True})

        # 管理者汇总
        summary_prompt = f"汇总以下结果:\n" + "\n".join(results)
        summary = self.agents[manager].run(summary_prompt)
        return f"[{manager} Plan]: {plan[:300]}\n\n[Results]: {summary[:500]}"

    def broadcast_message(self, content: str):
        """向所有 Agent 广播"""
        for name, agent in self.agents.items():
            msg = AgentMessage(
                msg_type=MessageType.BROADCAST,
                sender_id="swarm",
                target_id=agent.id,
                content=content,
            )
            self.router.send(msg)

    def collect_responses(self, timeout: float = 5.0) -> List[str]:
        import time
        start = time.time()
        results = []
        while time.time() - start < timeout:
            for name, agent in self.agents.items():
                msgs = self.router.receive(agent.id)
                for m in msgs:
                    results.append(f"[{name}]: {m.content[:200]}")
            if results:
                break
            time.sleep(0.1)
        return results

    def run_swarm(self, task: str, mode: Optional[str] = None) -> str:
        """运行 Swarm"""
        mode = mode or self.mode
        if mode == SwarmMode.ROUTE:
            return self.route(task)
        elif mode == SwarmMode.COLLABORATE:
            return self.collaborate(task)
        elif mode == SwarmMode.COORDINATE:
            return self.coordinate(task, list(self.agents.keys())[0] if self.agents else "")
        return "Unknown mode"

    def status(self) -> dict:
        return {
            "name": self.name, "mode": self.mode,
            "agents": {n: a.id[:8] + ("(dead)" if not a.alive else "")
                       for n, a in self.agents.items()},
            "state_bus": self.state_bus.status(),
            "tasks_pending": len([t for t in self.tasks if t.status == "pending"]),
        }
