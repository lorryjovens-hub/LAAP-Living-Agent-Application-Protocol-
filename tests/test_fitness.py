"""
单元测试: LAAP 适应度评估器 (FitnessEvaluator)

覆盖:
  - FitnessEvaluator 核心评分
  - 各维度评分函数 (need, emotion, performance, stability, growth)
  - 综合适应度计算与报告
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
from laap.evaluation.fitness import FitnessEvaluator
from laap.agent.base import Agent, AgentConfig
from laap.cognition.needs import NeedDriveSystem, NeedType
from laap.cognition.emotion import EmotionGradient


# ═══════════════════════════════════════════════════════════════
# FitnessEvaluator 核心
# ═══════════════════════════════════════════════════════════════

class TestFitnessEvaluator:
    def test_init_default_weights(self):
        """初始化包含 5 个评分维度权重"""
        ev = FitnessEvaluator()
        assert len(ev.weights) == 5
        for name in ["need_satisfaction", "emotional_health", "performance",
                       "stability", "growth_rate"]:
            assert name in ev.weights

    def test_init_weights_sum_to_one(self):
        """默认权重和为 1"""
        ev = FitnessEvaluator()
        assert sum(ev.weights.values()) == pytest.approx(1.0)

    def test_custom_weights(self):
        """支持自定义权重"""
        weights = {"need_satisfaction": 0.5, "emotional_health": 0.5,
                   "performance": 0.0, "stability": 0.0, "growth_rate": 0.0}
        ev = FitnessEvaluator(weights=weights)
        assert ev.weights["need_satisfaction"] == 0.5

    def test_composite_fitness_empty_agent(self):
        """空 Agent 的适应度在 [0,1] 范围内"""
        ev = FitnessEvaluator()
        config = AgentConfig(name="test", tools_enabled=False)
        agent = Agent(config=config)
        fitness = ev.composite_fitness(agent)
        assert 0.0 <= fitness <= 1.0

    def test_composite_fitness_with_needs(self):
        """有需求系统时适应度合理"""
        ev = FitnessEvaluator()
        config = AgentConfig(name="test", tools_enabled=False)
        agent = Agent(config=config)
        agent.needs = NeedDriveSystem()
        # 所有需求满足
        for nt in NeedType:
            agent.needs.needs[nt].current_level = 0.95
        fitness = ev.composite_fitness(agent)
        assert 0.0 <= fitness <= 1.0
        assert fitness > 0.5  # 应该较高

    def test_composite_fitness_with_emotion(self):
        """有情绪梯度时适应度工作"""
        ev = FitnessEvaluator()
        config = AgentConfig(name="test", tools_enabled=False)
        agent = Agent(config=config)
        agent.emotion_gradient = EmotionGradient()
        agent.emotion_gradient.update(
            {nt.value: 0.9 for nt in NeedType}, task_success=0.9)
        fitness = ev.composite_fitness(agent)
        assert 0.0 <= fitness <= 1.0

    def test_composite_fitness_with_reward_history(self):
        """有奖励历史时 performance 维度工作"""
        ev = FitnessEvaluator()
        config = AgentConfig(name="test", tools_enabled=False)
        agent = Agent(config=config)
        eg = EmotionGradient()
        for i in range(30):
            sats = {nt.value: min(1.0, 0.3 + i * 0.02) for nt in NeedType}
            eg.update(sats, task_success=0.5 + i * 0.01)
            eg.compute_intrinsic_reward()
        agent.emotion_gradient = eg
        score = ev._performance_score(agent)
        assert 0.0 <= score <= 1.0

    def test_need_score_high_when_satisfied(self):
        """需求满足度高时 need_score 高"""
        ev = FitnessEvaluator()
        config = AgentConfig(name="test", tools_enabled=False)
        agent = Agent(config=config)
        agent.needs = NeedDriveSystem()
        for nt in NeedType:
            agent.needs.needs[nt].current_level = 0.95
        score = ev._need_score(agent)
        assert score > 0.6

    def test_need_score_low_when_unsatisfied(self):
        """需求满足度低时 need_score 低"""
        ev = FitnessEvaluator()
        config = AgentConfig(name="test", tools_enabled=False)
        agent = Agent(config=config)
        agent.needs = NeedDriveSystem()
        for nt in NeedType:
            agent.needs.needs[nt].current_level = 0.05
        score = ev._need_score(agent)
        assert score < 0.4

    def test_need_score_no_needs(self):
        """没有需求系统时返回默认值 0.5"""
        ev = FitnessEvaluator()
        config = AgentConfig(name="test", tools_enabled=False)
        agent = Agent(config=config)
        score = ev._need_score(agent)
        assert score == 0.5

    def test_emotion_score_high_when_positive(self):
        """正向情绪时 emotion_score 高"""
        ev = FitnessEvaluator()
        config = AgentConfig(name="test", tools_enabled=False)
        agent = Agent(config=config)
        eg = EmotionGradient()
        eg.update({nt.value: 0.9 for nt in NeedType}, task_success=0.9)
        agent.emotion_gradient = eg
        score = ev._emotion_score(agent)
        assert score > 0.6

    def test_emotion_score_no_emotion(self):
        """没有情绪系统时返回默认 0.5"""
        ev = FitnessEvaluator()
        config = AgentConfig(name="test", tools_enabled=False)
        agent = Agent(config=config)
        score = ev._emotion_score(agent)
        assert score == 0.5

    def test_report_structure(self):
        """report 返回完整结构"""
        ev = FitnessEvaluator()
        config = AgentConfig(name="test", tools_enabled=False)
        agent = Agent(config=config)
        report = ev.report(agent)
        assert "fitness" in report
        assert "scores" in report
        assert isinstance(report["fitness"], float)
        assert isinstance(report["scores"], dict)
        assert len(report["scores"]) == 5

    def test_report_fitness_in_range(self):
        """report 的 fitness 在 [0, 1] 范围内"""
        ev = FitnessEvaluator()
        for _ in range(10):
            config = AgentConfig(name="test", tools_enabled=False)
            agent = Agent(config=config)
            report = ev.report(agent)
            assert 0.0 <= report["fitness"] <= 1.0

    def test_stability_score(self):
        """stability_score 在合理范围"""
        ev = FitnessEvaluator()
        config = AgentConfig(name="test", tools_enabled=False)
        agent = Agent(config=config)
        score = ev._stability_score(agent)
        assert 0.0 <= score <= 1.0

    def test_growth_score(self):
        """growth_score 在合理范围"""
        ev = FitnessEvaluator()
        config = AgentConfig(name="test", tools_enabled=False)
        agent = Agent(config=config)
        score = ev._growth_score(agent)
        assert 0.0 <= score <= 1.0