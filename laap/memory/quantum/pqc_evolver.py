"""QLAM — 参数量子电路 (PQC) 演化器"""
from __future__ import annotations
import numpy as np
from laap.memory.quantum.quantum_state import QuantumState, _ry, _rx, _rz


class PQCEvolver:
    """PQC 演化: |ψ_t⟩ = U(x_t, θ)·|ψ_{t-1}⟩

    电路: 输入编码层 → [Rot + CNOT] × n_layers
    """

    def __init__(self, n_qubits: int = 4, n_layers: int = 3):
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        self.params = np.random.randn(n_layers, n_qubits, 3).astype(np.float64) * 0.1

    def evolve(self, state: QuantumState, input_encoding: np.ndarray,
               params: np.ndarray | None = None) -> QuantumState:
        p = params if params is not None else self.params
        r = state.copy()
        # 编码层
        for i in range(self.n_qubits):
            r.apply_single_gate(_ry(input_encoding[i % len(input_encoding)]), i)
        # 变分层
        for layer in range(self.n_layers):
            for i in range(self.n_qubits):
                rx, ry, rz = p[layer, i]
                r.apply_single_gate(_rx(rx), i)
                r.apply_single_gate(_ry(ry), i)
                r.apply_single_gate(_rz(rz), i)
            for i in range(self.n_qubits - 1):
                r.apply_cnot(control=i, target=i + 1)
        return r

    def param_count(self) -> int:
        return self.n_layers * self.n_qubits * 3
