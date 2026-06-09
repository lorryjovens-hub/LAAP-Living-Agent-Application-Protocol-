"""AEvo — Evolution Harness + RunPlan

标准化进化框架: 受保护评估 + 候选历史 + Meta-Agent 编辑 + CLI 启停
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

from laap.evolution.aevo.candidate_history import CandidateHistory, CandidateRecord
from laap.evolution.aevo.protected_eval import ProtectedEvaluator

logger = logging.getLogger("laap.evolution.aevo.harness")


@dataclass
class RunPlan:
    """AEvo 运行计划 — 控制进化段的执行参数"""
    iterations: int = 20
    focus_area: str = "explore"
    termination_condition: str = "iterations"
    parameter_overrides: Dict[str, Any] = field(default_factory=dict)
    meta_notes: str = ""


class EvolutionHarness:
    """AEvo 进化 Harness

    组装所有组件并提供统一 run_segment 接口
    """

    def __init__(self, base_evolution=None, evaluator=None, meta_editor=None):
        self.base_evolution = base_evolution  # RSIEngine
        self.evaluator = evaluator or ProtectedEvaluator(None)
        self.meta_editor = meta_editor
        self.history = CandidateHistory()
        self.run_plan: Optional[RunPlan] = None
        self.running = False
        self._segment_results: List[CandidateRecord] = []

    def run_segment(self, agent, iterations: Optional[int] = None) -> List[CandidateRecord]:
        """运行一段进化迭代

        每次迭代:
          1. 检查 Meta-Edit 条件
          2. 生成候选 → 评估 → 记录
        """
        self.running = True
        n = iterations or (self.run_plan.iterations if self.run_plan else 20)
        results: List[CandidateRecord] = []

        for i in range(n):
            if not self.running:
                break

            # Meta-Edit check
            if self.meta_editor and self.meta_editor.should_edit(getattr(agent, 'step_count', 0)):
                new_plan = self.meta_editor.meta_edit(agent, self.history)
                if new_plan:
                    self.run_plan = new_plan

            # Apply parameter overrides
            if self.run_plan and self.run_plan.parameter_overrides:
                for k, v in self.run_plan.parameter_overrides.items():
                    if hasattr(agent.config, k):
                        setattr(agent.config, k, v)

            # Generate candidate & evaluate
            candidate = self.base_evolution.generate_candidate(agent) if self.base_evolution else None
            score, valid = self.evaluator.evaluate(agent, candidate)

            fb = self.history.candidates[-1].fitness_after if self.history.candidates else 0.5
            record = self.history.record_result(
                step=getattr(agent, 'step_count', 0),
                description=str(candidate)[:100] if candidate else "",
                fitness_before=fb,
                fitness_after=score,
                success=valid and score > 0.3,
            )
            results.append(record)

            if hasattr(agent, 'step'):
                try:
                    agent.step()
                except TypeError:
                    pass

        self._segment_results = results
        self.running = False
        return results

    def stop(self) -> None:
        self.running = False

    def status(self) -> dict:
        return {
            "running": self.running,
            "run_plan": {"iterations": self.run_plan.iterations,
                         "focus": self.run_plan.focus_area} if self.run_plan else None,
            "history": self.history.summary(),
            "evaluator": self.evaluator.status(),
            "segment_results": len(self._segment_results),
        }
