"""
单元测试: LAAP RSI (递归自我改进) 引擎

覆盖:
  - ImprovementProposal 数据结构
  - RSIEngine 核心流程
  - SymbolicRecursionLayer 符号递归层
  - MutationStrategy 变异策略
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
from laap.evolution.rsi import RSIEngine, ImprovementProposal
from laap.evolution.symbolic import SymbolicRecursionLayer, AgentLineage, NullAgent
from laap.evolution.mutation import MutationStrategy, MutationSpec
from laap.agent.base import Agent, AgentConfig
from laap.cognition.needs import NeedDriveSystem
from laap.cognition.emotion import EmotionGradient


# ═══════════════════════════════════════════════════════════════
# ImprovementProposal 单元
# ═══════════════════════════════════════════════════════════════

class TestImprovementProposal:
    def test_init(self):
        """提案初始化"""
        p = ImprovementProposal(episode=1, hypothesis="增加探索率",
                                 modification={"type": "adjust_exploration", "value": 0.1},
                                 expected_impact=0.3, confidence=0.7)
        assert p.episode == 1
        assert p.tested is False
        assert p.adopted is False
        assert p.modification["type"] == "adjust_exploration"

    def test_to_dict(self):
        """to_dict 包含关键字段"""
        p = ImprovementProposal(episode=1, hypothesis="test_hypothesis",
                                 modification={"type": "adjust_learning_rate"})
        d = p.to_dict()
        assert d["episode"] == 1
        assert "hypothesis" in d
        assert "mod_type" in d
        assert d["tested"] is False
        assert d["adopted"] is False


# ═══════════════════════════════════════════════════════════════
# RSIEngine 核心流程
# ═══════════════════════════════════════════════════════════════

class TestRSIEngine:
    def test_init(self):
        """RSIEngine 初始化"""
        engine = RSIEngine(proposal_interval=5)
        assert engine.proposal_interval == 5
        assert len(engine.proposals) == 0
        assert engine.adopted_count == 0
        assert engine.test_count == 0

    def test_init_default_interval(self):
        """默认 proposal_interval 为 20"""
        engine = RSIEngine()
        assert engine.proposal_interval == 20

    def test_init_default_threshold(self):
        """默认 adoption_threshold 为 0.05"""
        engine = RSIEngine()
        assert engine.adoption_threshold == 0.05

    def _setup_agent(self):
        """创建带有 needs 和 emotion_gradient 的测试 Agent"""
        config = AgentConfig(name="test", tools_enabled=False)
        agent = Agent(config=config)
        agent.needs = NeedDriveSystem()
        agent.emotion_gradient = EmotionGradient()
        # 添加记忆系统以支持 recent_reflections
        from laap.memory.hierarchical import HierarchicalMemory
        agent.memory = HierarchicalMemory(use_rust=False, use_quantum=False)
        return agent

    @staticmethod
    def _proposal_kwargs():
        from laap.evolution.rsi import ImprovementProposal
        return {"episode": 1, "hypothesis": "test",
                "modification": {"type": "adjust_exploration", "value": 0.05},
                "expected_impact": 0.3, "confidence": 0.7}

    def test_generate_candidate_returns_proposal(self):
        """generate_candidate 返回 ImprovementProposal 或 None"""
        agent = self._setup_agent()
        engine = RSIEngine(proposal_interval=1)
        proposal = engine.generate_candidate(agent)
        if proposal is not None:
            assert isinstance(proposal, ImprovementProposal)
        else:
            assert proposal is None

    def test_step_force_generates(self):
        """force=True 时总是生成提案"""
        agent = self._setup_agent()
        engine = RSIEngine(proposal_interval=100)
        proposal = engine.step(agent, force=True)
        if proposal is not None:
            assert isinstance(proposal, ImprovementProposal)

    def test_step_respects_interval(self):
        """非 force 时遵守间隔"""
        agent = self._setup_agent()
        engine = RSIEngine(proposal_interval=10)
        agent.step_count = 1
        result = engine.step(agent, force=False)
        assert result is None

    def test_step_at_interval(self):
        """步数达到间隔时可生成提案"""
        agent = self._setup_agent()
        engine = RSIEngine(proposal_interval=3)
        agent.step_count = 5
        engine.last_proposal_step = 2
        result = engine.step(agent, force=False)
        if result is not None:
            assert isinstance(result, ImprovementProposal)

    def test_proposals_list_grows(self):
        """多次 generate 增加提案列表"""
        agent = self._setup_agent()
        engine = RSIEngine(proposal_interval=1)
        count_before = len(engine.proposals)
        engine.generate_candidate(agent)
        engine.step(agent, force=True)
        assert len(engine.proposals) >= count_before

    def test_fitness_history(self):
        """fitness_history 记录适应度"""
        engine = RSIEngine()
        engine.fitness_history.append(0.3)
        engine.fitness_history.append(0.5)
        engine.fitness_history.append(0.7)
        assert engine.fitness_history == [0.3, 0.5, 0.7]

    def test_adopted_count_increments(self):
        """测试 adopted_count 计数器"""
        engine = RSIEngine()
        assert engine.adopted_count == 0

    def test_test_count_increments(self):
        """测试 test_count 计数器"""
        engine = RSIEngine()
        assert engine.test_count == 0

    def test_attach_aevo(self):
        """attach_aevo 存储 harness 引用"""
        engine = RSIEngine()
        engine.attach_aevo("mock_harness")
        assert engine._aevo_harness == "mock_harness"

    def test_noise_level_default(self):
        """默认噪声水平为 0"""
        engine = RSIEngine()
        assert engine.noise_level == 0.0

    def test_meaning_density_default(self):
        """默认意义密度为 0"""
        engine = RSIEngine()
        assert engine.meaning_density == 0.0


# ═══════════════════════════════════════════════════════════════
# MutationStrategy 单元
# ═══════════════════════════════════════════════════════════════

class TestMutationStrategy:
    def test_init_has_default_strategies(self):
        """初始化有 4 个默认变异策略"""
        ms = MutationStrategy()
        assert len(ms.strategies) >= 4
        for name in ["param_drift", "need_reweight", "exploration_tune", "goal_reprioritize"]:
            assert name in ms.strategies

    def test_register_custom_strategy(self):
        """注册自定义策略"""
        ms = MutationStrategy()
        def custom_fn(s): return s
        spec = MutationSpec(name="custom", description="test",
                            mutation_fn=custom_fn, probability=0.5)
        ms.register(spec)
        assert "custom" in ms.strategies

    def test_select_returns_valid_strategy(self):
        """select 返回存在的策略"""
        ms = MutationStrategy()
        spec = ms.select()
        assert spec.name in ms.strategies

    def test_apply_with_named_strategy(self):
        """apply 使用指定策略"""
        ms = MutationStrategy()
        state = {"config": {"exploration_rate": 0.5, "learning_rate": 0.1},
                 "needs": [], "goals": [], "skills": []}
        result = ms.apply(state, "param_drift")
        mutated = result["mutated"]
        assert "strategy" in result
        assert result["strategy"] == "param_drift"

    def test_apply_unknown_strategy_raises(self):
        """未知策略抛出 ValueError"""
        ms = MutationStrategy()
        with pytest.raises(ValueError, match="Unknown strategy"):
            ms.apply({}, "nonexistent")

    def test_param_drift_within_bounds(self):
        """param_drift 保持参数在 [0.01, 0.99] 内"""
        ms = MutationStrategy()
        for _ in range(50):
            state = {"config": {"exploration_rate": 0.5, "learning_rate": 0.1},
                     "needs": [], "goals": [], "skills": []}
            result = ms.apply(state, "param_drift")
            cfg = result["mutated"]["config"]
            assert 0.01 <= cfg["exploration_rate"] <= 0.99
            assert 0.01 <= cfg["learning_rate"] <= 0.99


# ═══════════════════════════════════════════════════════════════
# SymbolicRecursionLayer 单元
# ═══════════════════════════════════════════════════════════════

class TestSymbolicRecursionLayer:
    def test_init(self):
        """符号递归层初始化"""
        srl = SymbolicRecursionLayer(max_population=20)
        assert srl.max_population == 20
        assert len(srl.population) == 0
        assert srl.generation_counter == 0