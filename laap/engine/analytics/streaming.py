"""Streaming Summary Algorithms"""
from __future__ import annotations
import math, hashlib, time, json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

class CountMinSketch:
    """Count-Min Sketch: frequency estimation with minimal memory"""
    def __init__(self, width: int = 2000, depth: int = 10):
        self.width = width
        self.depth = depth
        self.table = [[0] * width for _ in range(depth)]
        self.total = 0
    def add(self, item: str, count: int = 1):
        self.total += count
        for i in range(self.depth):
            h = hash(f"{i}_{item}") % self.width
            self.table[i][h] += count
    def estimate(self, item: str) -> int:
        return min(self.table[i][hash(f"{i}_{item}") % self.width] for i in range(self.depth))
    def merge(self, other: "CountMinSketch"):
        if self.width != other.width or self.depth != other.depth:
            raise ValueError("Incompatible sketches")
        for i in range(self.depth):
            for j in range(self.width):
                self.table[i][j] += other.table[i][j]
        self.total += other.total

class HyperLogLog:
    """HyperLogLog: cardinality estimation"""
    def __init__(self, precision: int = 14):
        self.precision = precision
        self.m = 1 << precision
        self.registers = [0] * self.m
    def add(self, item: str):
        h = hash(item)
        idx = h & (self.m - 1)
        leading = (h >> self.precision).bit_length() if h >> self.precision else 1
        self.registers[idx] = max(self.registers[idx], leading)
    def estimate(self) -> int:
        alpha = 0.7213 / (1 + 1.079 / self.m)
        raw = alpha * self.m * self.m / sum(2.0 ** -r for r in self.registers)
        if raw < 2.5 * self.m:
            zeros = self.registers.count(0)
            if zeros:
                raw = self.m * math.log(self.m / zeros)
        return int(raw)

class TDigest:
    """T-Digest: percentile estimation"""
    def __init__(self, compression: int = 100):
        self.compression = compression
        self.centroids: List[tuple] = []
    def add(self, value: float, weight: int = 1):
        self.centroids.append((value, weight))
        if len(self.centroids) > self.compression * 10:
            self._compress()
    def _compress(self):
        self.centroids.sort(key=lambda x: x[0])
        compressed = []
        total_weight = 0
        for val, w in self.centroids:
            total_weight += w
            if compressed:
                last_val, last_w = compressed[-1]
                if last_w + w <= total_weight / self.compression * 2:
                    merged = (last_val * last_w + val * w) / (last_w + w)
                    compressed[-1] = (merged, last_w + w)
                    continue
            compressed.append((val, w))
        self.centroids = compressed
    def percentile(self, p: float) -> float:
        if not self.centroids:
            return 0.0
        self.centroids.sort(key=lambda x: x[0])
        total = sum(w for _, w in self.centroids)
        target = total * p / 100.0
        cumulative = 0
        for val, w in self.centroids:
            cumulative += w
            if cumulative >= target:
                return val
        return self.centroids[-1][0]
