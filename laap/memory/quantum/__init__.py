"""QLAM — 量子长程注意力记忆

基于 "QLAM: A Quantum Long-Attention Memory Approach" (arXiv:2605.13833)
将 SSM 隐状态表示为量子态，通过 PQC 实现非经典更新。
"""
from laap.memory.quantum.quantum_state import QuantumState
from laap.memory.quantum.pqc_evolver import PQCEvolver
from laap.memory.quantum.quantum_memory import QLAMMemory, QuantumEncoder, QuantumMeasurement

__all__ = ["QuantumState", "PQCEvolver", "QLAMMemory", "QuantumEncoder", "QuantumMeasurement"]
