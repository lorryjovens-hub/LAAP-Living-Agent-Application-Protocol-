"""
LAAP ⟷ QLAM — Quantum State Encoding
Encodes hidden states as quantum amplitude vectors.
"""

from __future__ import annotations
import math
from typing import List, Optional


class AmplitudeEncoding:
    def __init__(self, num_qubits: int = 6):
        self.num_qubits = num_qubits
        self.dim = 1 << num_qubits

    def encode(self, vector: List[float]) -> List[float]:
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector[:self.dim]]

    def decode(self, amplitudes: List[float]) -> List[float]:
        return list(amplitudes)


class QuantumStateEncoder:
    def __init__(self, encoding_dim: int = 64, num_qubits: Optional[int] = None):
        self.encoding_dim = encoding_dim
        num_qubits = num_qubits or max(4, int(math.log2(encoding_dim)) + 1)
        self.amplitude = AmplitudeEncoding(num_qubits)

    def encode(self, classical_data: List[float]) -> List[float]:
        return self.amplitude.encode(classical_data[:self.encoding_dim])

    def decode(self, quantum_state: List[float]) -> List[float]:
        return self.amplitude.decode(quantum_state)[:self.encoding_dim]
