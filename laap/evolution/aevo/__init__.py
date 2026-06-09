"""AEvo — Agent 自进化元编辑框架核心组件

基于 "Harnessing Agentic Evolution" (arXiv:2605.13821) 的两阶段循环:
  1. Meta-Editing Phase — Meta-Agent 观察进化上下文并编辑进化机制
  2. Evolution Segment — 更新后的机制运行多次迭代产生候选
"""
from laap.evolution.aevo.candidate_history import CandidateRecord, CandidateHistory
from laap.evolution.aevo.protected_eval import ProtectedEvaluator
from laap.evolution.aevo.meta_editor import MetaEditor, EditPlan, EditTarget
from laap.evolution.aevo.harness import EvolutionHarness, RunPlan

__all__ = [
    "CandidateRecord", "CandidateHistory",
    "ProtectedEvaluator",
    "MetaEditor", "EditPlan", "EditTarget",
    "EvolutionHarness", "RunPlan",
]
