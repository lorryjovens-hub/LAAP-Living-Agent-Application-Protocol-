"""集成测试: AEvo 和 QLAM 模块"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np


class TestAEvo:
    """AEvo 元编辑引擎测试"""

    def test_candidate_history(self):
        from laap.evolution.aevo import CandidateHistory
        h = CandidateHistory(max_size=10)
        h.record_result(step=1, fitness_before=0.5, fitness_after=0.6, success=True)
        assert len(h.candidates) == 1
        assert len(h.fitness_trend()) == 1

    def test_candidate_eviction(self):
        from laap.evolution.aevo import CandidateHistory
        h = CandidateHistory(max_size=10)
        for i in range(20):
            h.record_result(step=i, fitness_before=0.5, fitness_after=0.5+0.01*i, success=True)
        assert len(h.candidates) == 10
        assert len(h.best_k(3)) == 3

    def test_failure_patterns(self):
        from laap.evolution.aevo import CandidateHistory
        h = CandidateHistory()
        h.record_result(step=1, fitness_before=0.5, fitness_after=0.4, success=False, error="timeout")
        h.record_result(step=2, fitness_before=0.4, fitness_after=0.3, success=False, error="timeout")
        assert len(h.failure_patterns()) == 1
        assert "timeout" in h.failure_patterns()[0]

    def test_protected_evaluator(self):
        from laap.evolution.aevo import ProtectedEvaluator
        from laap.evaluation.fitness import FitnessEvaluator
        class MockAgent:
            class Config:
                exploration_rate = 0.2
                learning_rate = 0.1
            config = Config()
        pe = ProtectedEvaluator(FitnessEvaluator())
        score, valid = pe.evaluate(MockAgent())
        assert valid and 0 <= score <= 1
        assert not pe._validate({"__builtins__": "danger"})

    def test_meta_editor_rule(self):
        from laap.evolution.aevo import MetaEditor
        editor = MetaEditor(llm_provider=None, edit_interval=10)
        assert editor.should_edit(10)
        assert not editor.should_edit(5)
        plan = editor._rule_analyze({
            "fitness_history": [0.5, 0.49, 0.48, 0.47, 0.46],
            "exploration_rate": 0.2, "learning_rate": 0.1,
        })
        assert plan is not None
        assert plan.hypothesis

    def test_meta_editor_rising(self):
        from laap.evolution.aevo import MetaEditor
        editor = MetaEditor()
        plan = editor._rule_analyze({
            "fitness_history": [0.4, 0.42, 0.45, 0.48, 0.52],
            "exploration_rate": 0.2, "learning_rate": 0.1,
        })
        assert plan is not None
        assert plan.focus_area == "exploit"

    def test_evolution_harness(self):
        from laap.evolution.aevo import EvolutionHarness, RunPlan
        rp = RunPlan(iterations=10)
        assert rp.iterations == 10
        harness = EvolutionHarness()
        assert "history" in harness.status()

    def test_harness_segment(self):
        from laap.evolution.aevo import EvolutionHarness, ProtectedEvaluator
        from laap.evaluation.fitness import FitnessEvaluator
        class MockRSI:
            def generate_candidate(self, agent):
                return {"type": "test"}
        class MockAgent:
            class Config:
                exploration_rate = 0.2
                learning_rate = 0.1
            config = Config()
            step_count = 0
            def step(self):
                self.step_count += 1
        pe = ProtectedEvaluator(FitnessEvaluator())
        harn = EvolutionHarness(base_evolution=MockRSI(), evaluator=pe)
        results = harn.run_segment(MockAgent(), iterations=3)
        assert len(results) == 3

    def test_rsi_aevo_integration(self):
        from laap.evolution.rsi import RSIEngine
        rsi = RSIEngine()
        assert hasattr(rsi, 'generate_candidate')
        assert hasattr(rsi, 'attach_aevo')

    def test_package_exports(self):
        from laap.evolution import (
            EvolutionHarness, MetaEditor, CandidateHistory,
            RSIEngine, SymbolicRecursionLayer, Sandbox
        )
        assert EvolutionHarness is not None


class TestQLAM:
    """QLAM 量子记忆测试"""

    def test_quantum_state(self):
        from laap.memory.quantum import QuantumState
        qs = QuantumState(n_qubits=4)
        assert abs(np.linalg.norm(qs.amplitudes) - 1.0) < 1e-10
        assert qs.amplitudes[0] == 1.0
        assert qs.entropy() < 1e-6

    def test_quantum_state_copy(self):
        from laap.memory.quantum import QuantumState
        qs = QuantumState(4)
        qs2 = qs.copy()
        assert qs.fidelity(qs2) > 0.999

    def test_pqc_evolver(self):
        from laap.memory.quantum import PQCEvolver, QuantumState
        pqc = PQCEvolver(n_qubits=4, n_layers=2)
        assert pqc.param_count() == 24
        state = QuantumState(4)
        new_state = pqc.evolve(state, np.array([0.5, 0.3, 0.8, 0.1]))
        assert new_state.entropy() > 0.1

    def test_qlam_memory(self):
        from laap.memory.quantum import QLAMMemory
        ql = QLAMMemory(n_qubits=4, n_layers=2)
        out = ql.update_from_text("hello quantum world")
        assert len(out) == 4
        out2 = ql.update_from_text("machine learning")
        assert ql.state.entropy() > 0.1
        ret = ql.retrieve(np.array([0.5, 0.3, 0.8, 0.1]), k=2)
        assert len(ret) <= 2

    def test_qlam_status(self):
        from laap.memory.quantum import QLAMMemory
        ql = QLAMMemory(n_qubits=4)
        s = ql.status()
        assert s["n_qubits"] == 4
        assert s["steps"] == 0


class TestIntegration:
    """AEvo + QLAM 与 LAAP 集成测试"""

    def test_memory_quantum_init(self):
        from laap.memory.hierarchical import HierarchicalMemory
        hm = HierarchicalMemory(use_quantum=True, n_qubits=4)
        assert hm is not None

    def test_memory_quantum_remember(self):
        from laap.memory.hierarchical import HierarchicalMemory
        hm = HierarchicalMemory(use_quantum=True, n_qubits=4)
        hm.remember("quantum physics", tags=["q"], importance=0.8)
        assert len(hm.episodic) == 1
        if hm._quantum:
            assert len(hm._quantum.input_history) == 1

    def test_memory_quantum_recall(self):
        from laap.memory.hierarchical import HierarchicalMemory
        hm = HierarchicalMemory(use_quantum=True, n_qubits=4)
        hm.remember("test a", tags=["a"], importance=0.8)
        hm.remember("test b", tags=["b"], importance=0.7)
        qr = hm.quantum_recall("test", k=2)
        assert isinstance(qr, list)

    def test_memory_plain_still_works(self):
        from laap.memory.hierarchical import HierarchicalMemory
        hm = HierarchicalMemory(use_quantum=False)
        hm.remember("plain memory", tags=["p"], importance=0.5)
        r = hm.recall(query_tags=["p"])
        assert len(r) == 1

    def test_rsi_imports_ok(self):
        from laap.evolution.rsi import RSIEngine
        rsi = RSIEngine()
        s = rsi.status()
        assert "total" in s
