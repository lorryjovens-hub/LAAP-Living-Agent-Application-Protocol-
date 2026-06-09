"""
LAAP — LifelikeAgent：类生命意识 Agent

融合 PSI 认知架构的"有意识"Agent：
  - 内在需求驱动行为
  - 情绪从需求满足中涌现
  - 自我感知与环境感知
  - LLM 作为"思考皮层"
  - RSI 作为"进化引擎"
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import logging, numpy as np

from laap.agent.base import Agent, AgentConfig
from laap.cognition.needs import NeedDriveSystem, NeedType
from laap.cognition.emotion import EmotionGradient
from laap.cognition.goals import GoalTree, Goal, GoalStatus
from laap.evolution.rsi import RSIEngine, ImprovementProposal
from laap.evaluation.fitness import FitnessEvaluator

logger = logging.getLogger("laap.agent.lifelike")


@dataclass
class LifelikeConfig(AgentConfig):
    need_config: Optional[Dict[str, dict]] = None
    rsi_enabled: bool = True
    rsi_interval: int = 20
    reflection_interval: int = 10


class LifelikeAgent(Agent):
    """具有 PSI 认知架构的类生命 Agent"""

    def __init__(self, config: Optional[LifelikeConfig] = None,
                 llm_factory=None, show_banner: Optional[bool] = None):
        super().__init__(config or LifelikeConfig(), llm_factory,
                         show_banner=show_banner)
        self.config: LifelikeConfig = self.config  # type hint

        # PSI 子系统
        self.needs = NeedDriveSystem(self.config.need_config)
        self.emotion_gradient = EmotionGradient()
        self.goals = GoalTree()

        # RSI 引擎
        self.rsi = RSIEngine(
            proposal_interval=self.config.rsi_interval,
        ) if self.config.rsi_enabled else None

        # 评估器
        self.evaluator = FitnessEvaluator()

        # 内部状态
        self.current_action: Optional[str] = None
        self._action_history: List[str] = []
        self._reward_history: List[float] = []
        self._need_history: List[Dict[str, float]] = []

        # 注册类生命默认动作
        self._register_life_actions()

        logger.info(f"LifelikeAgent [{self.id[:8]}] PSI 认知引擎已启动")

    def _register_life_actions(self):
        """注册类生命的本能动作"""
        self.register_tool("explore", self._act_explore, "探索环境，发现新信息")
        self.register_tool("analyze", self._act_analyze, "分析已有信息，提取模式")
        self.register_tool("reflect", self._act_reflect, "反思自身，提升元认知")
        self.register_tool("rest", self._act_rest, "休息，恢复能量")

    def _act_explore(self, target: str = "") -> str:
        return f"探索 {target or '环境'}，收集到新信号"

    def _act_analyze(self, data: str = "") -> str:
        return f"分析完成: {data or '数据'}中存在结构模式"

    def _act_reflect(self, topic: str = "") -> str:
        return f"关于 {topic or '自我'}的反思: 理解了新的关联"

    def _act_rest(self, duration: int = 1) -> str:
        return f"休息 {duration} 回合，能量恢复"

    def step(self, observation: str, task_success: Optional[float] = None,
             tags: Optional[List[str]] = None) -> dict:
        """执行一部完整的认知循环：感知 -> 评估 -> 行动 -> 学习 -> [反思]"""
        if not self.alive:
            return {"status": "dead", "step": self.step_count}

        self.step_count += 1

        # 1. 感知
        self.memory.perceive(observation, tags, importance=0.5)
        self.memory.remember(observation, tags, importance=0.3)

        # 2. 需求评估与情绪更新
        drives = self.needs.tick()
        self._need_history.append(
            {nt.value: self.needs.needs[nt].current_level for nt in self.needs.needs}
        )

        deltas = {}
        if len(self._need_history) >= 2:
            for nt in self.needs.needs:
                k = nt.value
                deltas[k] = self._need_history[-1][k] - self._need_history[-2][k]

        satisfactions = {nt.value: self.needs.needs[nt].current_level for nt in self.needs.needs}
        emotional_state = self.emotion_gradient.update(satisfactions, task_success=task_success)
        intrinsic_reward = self.emotion_gradient.compute_intrinsic_reward()
        self._reward_history.append(intrinsic_reward)

        # 3. 行动选择
        action_selection = self._select_action()
        if action_selection:
            # action_selection can be (name, kwargs) tuple or just name (legacy)
            if isinstance(action_selection, tuple):
                action, action_kwargs = action_selection
            else:
                action, action_kwargs = action_selection, {}
            logger.info(
                f"[LifelikeAgent] step: selected action={action} "
                f"kwargs={list(action_kwargs.keys())} step={self.step_count}"
            )
            result = self.execute_action(action, **action_kwargs)
            self.current_action = action
            self._action_history.append(action)
        else:
            result = None

        # 4. 学习 (满足需求）
        self._satisfy_needs_from_action(action, task_success)

        # 5. (可选) 自我反思
        reflection = None
        if self.step_count % self.config.reflection_interval == 0:
            reflection = self._self_reflect()

        # 6. (可选) RSI 自我改进
        rsi_result = None
        if self.rsi and self.step_count % 5 == 0:
            rsi_result = self.rsi.step(self, force=(self.step_count % 20 == 0))

        return {
            "step": self.step_count,
            "action": action,
            "action_result": str(result)[:100] if result else None,
            "emotional_state": emotional_state.to_dict(),
            "dominant_need": self.needs.get_dominant_need()[0].value if self.needs.get_dominant_need()[0] else None,
            "intrinsic_reward": round(intrinsic_reward, 4),
            "total_reward": round(sum(self._reward_history), 3),
            "reflection": reflection.to_dict() if reflection else None,
            "rsi": rsi_result.to_dict() if rsi_result else None,
        }

    def _select_action(self) -> Optional[Any]:
        """需求驱动的行动选择 — 同时返回行动 + 智能默认参数"""
        # Filter out LLM-only internal tools from cognitive loop
        internal_tools = {"run_python", "apply_modification"}
        available = [a for a in self.tool_registry._tools.keys() if a not in internal_tools]
        if not available:
            return None

        import numpy as np
        if np.random.random() < (getattr(self.config, 'exploration_rate', 0.2)):
            action = np.random.choice(available)
            return (action, self._infer_default_args(action))

        dominant, _ = self.needs.get_dominant_need()
        confidence = self.emotion_gradient.state.confidence

        scores = {}
        for action in available:
            skill = self.memory.skills.get(action)
            prof = skill.proficiency if skill else 0.5
            conf_mod = 1.0 + (1.0 - confidence) * prof
            scores[action] = prof * conf_mod + np.random.normal(0, 0.05)

        best_action = max(scores, key=scores.get)
        return (best_action, self._infer_default_args(best_action))

    def _infer_default_args(self, action: str) -> dict:
        """根据工具签名推断默认参数，避免 missing-arg 错误"""
        try:
            tool = self.tool_registry._tools.get(action)
            if not tool or not tool.handler:
                return {}
            import inspect
            sig = inspect.signature(tool.handler)
            defaults: dict = {}
            for name, param in sig.parameters.items():
                if name == "self":
                    continue
                if param.default is inspect.Parameter.empty:
                    # Required parameter — provide context-aware default
                    pname = name.lower()
                    if "url" in pname:
                        defaults[name] = "https://example.com"
                    elif "path" in pname or "file" in pname:
                        defaults[name] = "README.md"
                    elif "command" in pname or "cmd" in pname:
                        defaults[name] = "echo hello"
                    elif "code" in pname or "script" in pname:
                        defaults[name] = "print('hello')"
                    elif "query" in pname or "text" in pname or "content" in pname:
                        defaults[name] = "hello"
                    else:
                        defaults[name] = "x"
                # If param has a default, omit it (use the default)
            logger.debug(
                f"[LifelikeAgent] _infer_default_args: action={action} "
                f"defaults={list(defaults.keys())}"
            )
            return defaults
        except Exception as e:
            logger.warning(f"[LifelikeAgent] _infer_default_args: failed for {action}: {e}")
            return {}

    def execute_action(self, action: str, **kwargs) -> Any:
        """执行动作并更新记忆"""
        result = self.call_tool(action, **kwargs)
        self.memory.record_skill_result(action, result is not None)
        return result

    def _satisfy_needs_from_action(self, action: Optional[str], task_success: Optional[float]):
        """根据行动结果满足需求"""
        if action == "explore":
            self.needs.satisfy(NeedType.CERTAINTY, 0.05)
            self.needs.satisfy(NeedType.COMPETENCE, 0.03)
        elif action == "analyze":
            self.needs.satisfy(NeedType.CERTAINTY, 0.08)
            self.needs.satisfy(NeedType.COMPETENCE, 0.06)
        elif action == "reflect":
            self.needs.satisfy(NeedType.AUTONOMY, 0.05)
            self.needs.satisfy(NeedType.COMPETENCE, 0.04)
        elif action == "rest":
            self.needs.satisfy(NeedType.ENERGY, 0.1)

        if task_success is not None and task_success > 0.7:
            self.needs.satisfy(NeedType.COMPETENCE, 0.05 * task_success)

    def _self_reflect(self) -> Any:
        """自我反思"""
        from laap.memory.hierarchical import Reflection
        recent = self._reward_history[-5:] if self._reward_history else [0]
        trend = recent[-1] - recent[0] if len(recent) >= 2 else 0
        vol = float(np.std(recent)) if len(recent) >= 2 else 0

        if trend < -0.2:
            obs, hyp = "奖励下降", "需要新策略满足需求"
        elif vol > 0.3:
            obs, hyp = "波动过大", "需要增加确定性需求"
        elif self.emotion_gradient.state.confidence < 0.3:
            obs, hyp = "置信度低", "需要更多数据"
        else:
            obs, hyp = "运行平稳", "可以尝试提升效率"

        ref = Reflection(episode=self.step_count, observation=obs, hypothesis=hyp,
                         outcome=f"trend={trend:.3f}, vol={vol:.3f}",
                         reward_delta=trend)
        self.memory.add_reflection(ref)
        return ref

    def apply_modification(self, modification: Dict[str, Any]) -> bool:
        """扩展基类以支持需求调整"""
        mod_type = modification.get("type")
        params = modification.get("params", {})
        try:
            if mod_type == "adjust_needs":
                for need_str, adjustments in params.items():
                    try:
                        nt = NeedType(need_str)
                    except ValueError:
                        continue
                    if nt in self.needs.needs:
                        for k, v in adjustments.items():
                            if hasattr(self.needs.needs[nt], k):
                                setattr(self.needs.needs[nt], k, v)
                self._self_modifications += 1
                return True
            else:
                return super().apply_modification(modification)
        except Exception as e:
            logger.error(f"Modification failed: {e}")
            return False

    def complete_status(self) -> dict:
        """完整状态报告"""
        s = super().status()
        s.update({
            "needs": self.needs.get_profile(),
            "emotional_state": self.emotion_gradient.state.to_dict(),
            "mean_reward": round(self.emotion_gradient.mean_reward, 4),
            "reward_volatility": round(self.emotion_gradient.reward_volatility, 4),
            "dominant_need": self.needs.get_dominant_need()[0].value if self.needs.get_dominant_need()[0] else None,
            "goals": self.goals.to_dict(),
            "rsi": self.rsi.status() if self.rsi else None,
            "fitness": self.evaluator.report(self) if self.evaluator else None,
        })
        return s

    @property
    def total_reward(self) -> float:
        return round(sum(self._reward_history), 2)
