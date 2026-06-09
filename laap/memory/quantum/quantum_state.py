"""QLAM — 量子态表示 (经典 NumPy 模拟)"""
from __future__ import annotations
import numpy as np
from typing import List, Optional, Tuple


def _rx(angle: float) -> np.ndarray:
    c, s = np.cos(angle/2), np.sin(angle/2)
    return np.array([[c, -1j*s], [-1j*s, c]], dtype=complex)


def _ry(angle: float) -> np.ndarray:
    c, s = np.cos(angle/2), np.sin(angle/2)
    return np.array([[c, -s], [s, c]], dtype=complex)


def _rz(angle: float) -> np.ndarray:
    c, s = np.cos(angle/2), np.sin(angle/2)
    return np.array([[c - 1j*s, 0], [0, c + 1j*s]], dtype=complex)


class QuantumState:
    """n 量子比特状态 |ψ⟩ = Σᵢ αᵢ|i⟩, |αᵢ|² 归一化"""

    def __init__(self, n_qubits: int = 4):
        self.n_qubits = n_qubits
        self.dim = 2 ** n_qubits
        self.amplitudes: np.ndarray = np.zeros(self.dim, dtype=complex)
        self.amplitudes[0] = 1.0  # |0...0⟩

    def reset(self) -> None:
        self.amplitudes.fill(0.0)
        self.amplitudes[0] = 1.0

    def apply_single_gate(self, gate: np.ndarray, qubit: int) -> None:
        op = 1
        for i in range(self.n_qubits):
            op = np.kron(op, gate if i == qubit else np.eye(2, dtype=complex))
        self.amplitudes = op @ self.amplitudes

    def apply_cnot(self, control: int, target: int) -> None:
        new = np.zeros_like(self.amplitudes)
        for i in range(self.dim):
            bits = [(i >> (self.n_qubits - 1 - j)) & 1 for j in range(self.n_qubits)]
            if bits[control] == 1:
                bits[target] = 1 - bits[target]
                idx = sum(b << (self.n_qubits - 1 - j) for j, b in enumerate(bits))
                new[idx] = self.amplitudes[i]
            else:
                new[i] = self.amplitudes[i]
        self.amplitudes = new

    def probs(self) -> np.ndarray:
        return np.abs(self.amplitudes) ** 2

    def expectation_z(self, qubit: int) -> float:
        p0 = sum(self.probs()[i] for i in range(self.dim)
                 if not ((i >> (self.n_qubits - 1 - qubit)) & 1))
        return 2.0 * p0 - 1.0

    def all_expectations_z(self) -> np.ndarray:
        return np.array([self.expectation_z(i) for i in range(self.n_qubits)])

    def entropy(self) -> float:
        p = self.probs()
        p = p[p > 0]
        return float(-np.sum(p * np.log2(p)))

    def fidelity(self, other: QuantumState) -> float:
        return float(np.abs(np.vdot(self.amplitudes, other.amplitudes)) ** 2)

    def copy(self) -> QuantumState:
        s = QuantumState(self.n_qubits)
        s.amplitudes = self.amplitudes.copy()
        return s

    def to_dict(self) -> dict:
        return {"n_qubits": self.n_qubits, "dim": self.dim,
                "norm": float(np.linalg.norm(self.amplitudes)),
                "entropy": round(self.entropy(), 4)}
