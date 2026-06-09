"""QLAM — 量子长程注意力记忆主类

将序列历史编码为量子叠加态，PQC 非经典更新，量子测量检索。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import hashlib, logging

from laap.memory.quantum.quantum_state import QuantumState
from laap.memory.quantum.pqc_evolver import PQCEvolver

logger = logging.getLogger("laap.memory.quantum")


class QuantumEncoder:
    """经典→量子编码器"""

    @staticmethod
    def angle_encode(data: np.ndarray, n_qubits: int) -> np.ndarray:
        d = np.asarray(data, dtype=np.float64)
        if len(d) == 0:
            return np.zeros(n_qubits)
        rng = max(np.max(np.abs(d)), 1e-8)
        d = d / rng * np.pi
        r = np.zeros(n_qubits, dtype=np.float64)
        n = min(len(d), n_qubits)
        r[:n] = d[:n]
        return r


class QuantumMeasurement:
    """量子测量与经典输出提取"""

    @staticmethod
    def measure_expectations(state: QuantumState) -> np.ndarray:
        return state.all_expectations_z()

    @staticmethod
    def retrieve_kernel(state: QuantumState, query: np.ndarray) -> float:
        exp = state.all_expectations_z()
        ns, nq = np.linalg.norm(exp), np.linalg.norm(query)
        if ns == 0 or nq == 0:
            return 0.0
        return float(np.dot(exp, query) / (ns * nq))


class QLAMMemory:
    """QLAM 量子长程注意力记忆

    x_t → QuantumEncoder → PQC Evolver → QuantumMeasurement → y_t
                              ↑
                          |ψ_{t-1}⟩
    """

    def __init__(self, n_qubits: int = 4, n_layers: int = 3):
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        self.encoder = QuantumEncoder()
        self.evolver = PQCEvolver(n_qubits, n_layers)
        self.measurement = QuantumMeasurement()
        self.state = QuantumState(n_qubits)
        self.state_history: List[np.ndarray] = []
        self.output_history: List[np.ndarray] = []
        self.input_history: List[str] = []
        logger.info(f"QLAMMemory: {n_qubits} qubits, {n_layers} layers, "
                    f"{self.evolver.param_count()} params")

    def forward(self, input_data: np.ndarray) -> np.ndarray:
        encoding = self.encoder.angle_encode(input_data, self.n_qubits)
        self.state = self.evolver.evolve(self.state, encoding)
        output = self.measurement.measure_expectations(self.state)
        self.state_history.append(self.state.amplitudes.copy())
        self.output_history.append(output)
        return output

    def update_from_text(self, text: str) -> np.ndarray:
        d = hashlib.md5(text.encode()).digest()
        emb = np.frombuffer(d, dtype=np.uint8).astype(np.float64)[:self.n_qubits] / 255.0
        out = self.forward(emb)
        self.input_history.append(text[:50])
        return out

    def retrieve(self, query: np.ndarray, k: int = 5) -> List[Tuple[int, float]]:
        if not self.state_history:
            return []
        qe = self.encoder.angle_encode(query, self.n_qubits)
        sims = []
        for i, amps in enumerate(self.state_history):
            s = QuantumState(self.n_qubits)
            s.amplitudes = amps.copy()
            sim = self.measurement.retrieve_kernel(s, qe)
            sims.append((i, sim))
        sims.sort(key=lambda x: x[1], reverse=True)
        return sims[:k]

    def status(self) -> dict:
        return {
            "n_qubits": self.n_qubits,
            "n_layers": self.n_layers,
            "param_count": self.evolver.param_count(),
            "entropy": round(self.state.entropy(), 4),
            "steps": len(self.state_history),
        }
