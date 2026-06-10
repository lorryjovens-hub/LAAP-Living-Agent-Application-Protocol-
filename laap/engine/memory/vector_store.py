"""
Vector Store Abstraction Layer - Multiple vector DB backends
"""
from __future__ import annotations
import time, json, logging, abc, math, threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("engine.memory.vector_store")

class DistanceMetric(str, Enum):
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"

@dataclass
class VectorRecord:
    id: str = ""
    vector: List[float] = field(default_factory=list)
    payload: Dict = field(default_factory=dict)
    score: float = 0.0
    created_at: float = field(default_factory=time.time)

class VectorStore(abc.ABC):
    @abc.abstractmethod
    def store(self, record: VectorRecord) -> str:
        pass
    @abc.abstractmethod
    def search(self, query_vector: List[float], top_k: int = 10) -> List[VectorRecord]:
        pass
    @abc.abstractmethod
    def delete(self, record_id: str) -> bool:
        pass
    @abc.abstractmethod
    def count(self) -> int:
        pass

class MemoryVectorStore(VectorStore):
    def __init__(self, dimension: int = 384, metric: DistanceMetric = DistanceMetric.COSINE):
        self._records: Dict[str, VectorRecord] = {}
        self.dimension = dimension
        self.metric = metric
        self._lock = threading.RLock()

    def store(self, record: VectorRecord) -> str:
        with self._lock:
            self._records[record.id] = record
        return record.id

    def search(self, query_vector: List[float], top_k: int = 10, metric: Optional[DistanceMetric] = None) -> List[VectorRecord]:
        m = metric or self.metric
        scored = []
        with self._lock:
            for rec in self._records.values():
                if m == DistanceMetric.COSINE:
                    dot = sum(a*b for a,b in zip(query_vector, rec.vector))
                    n1 = math.sqrt(sum(a*a for a in query_vector))
                    n2 = math.sqrt(sum(b*b for b in rec.vector))
                    score = dot/(n1*n2) if (n1*n2) > 0 else 0.0
                elif m == DistanceMetric.EUCLIDEAN:
                    score = -math.sqrt(sum((a-b)**2 for a,b in zip(query_vector, rec.vector)))
                else:
                    score = sum(a*b for a,b in zip(query_vector, rec.vector))
                scored.append((rec, score))
        scored.sort(key=lambda x: -x[1])
        for rec, score in scored[:top_k]:
            rec.score = score
        return [rec for rec, _ in scored[:top_k]]

    def delete(self, record_id: str) -> bool:
        with self._lock:
            return self._records.pop(record_id, None) is not None

    def count(self) -> int:
        with self._lock:
            return len(self._records)

class QdrantStore(VectorStore):
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.host = host
        self.port = port
        self._records: Dict[str, VectorRecord] = {}
    def store(self, record: VectorRecord) -> str:
        self._records[record.id] = record
        return record.id
    def search(self, query_vector: List[float], top_k: int = 10) -> List[VectorRecord]:
        return []
    def delete(self, record_id: str) -> bool:
        return self._records.pop(record_id, None) is not None
    def count(self) -> int:
        return len(self._records)

class ChromaStore(VectorStore):
    def __init__(self, persist_dir: str = "./chroma_data"):
        self.persist_dir = persist_dir
        self._records: Dict[str, VectorRecord] = {}
    def store(self, record: VectorRecord) -> str:
        self._records[record.id] = record
        return record.id
    def search(self, query_vector: List[float], top_k: int = 10) -> List[VectorRecord]:
        scored = [(rec, sum(a*b for a,b in zip(query_vector, rec.vector))) for rec in self._records.values()]
        scored.sort(key=lambda x: -x[1])
        return [rec for rec,_ in scored[:top_k]]
    def delete(self, record_id: str) -> bool:
        return self._records.pop(record_id, None) is not None
    def count(self) -> int:
        return len(self._records)

class EmbeddingProvider(abc.ABC):
    @abc.abstractmethod
    def embed(self, text: str) -> List[float]:
        pass
    @abc.abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass
