"""
LAAP — Vector Database Adapter

Abstract interface for vector database backends.
Supports Qdrant (primary) and in-memory (fallback).
"""

from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger("laap.rag.db")


class VectorDB(ABC):
    @abstractmethod
    def create_collection(self, name: str, dimension: int) -> bool:
        ...

    @abstractmethod
    def upsert(self, collection: str, points: List[Dict]) -> bool:
        ...

    @abstractmethod
    def search(self, collection: str, vector: List[float],
               top_k: int = 10) -> List[Dict]:
        ...

    @abstractmethod
    def delete_collection(self, name: str) -> bool:
        ...


class QdrantDB(VectorDB):
    """Qdrant vector database backend"""

    def __init__(self, url: str = "http://localhost:6333",
                 api_key: Optional[str] = None):
        self.url = url
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is None:
            from qdrant_client import QdrantClient
            self._client = QdrantClient(
                url=self.url,
                api_key=self.api_key,
            )
        return self._client

    def create_collection(self, name: str, dimension: int) -> bool:
        from qdrant_client.models import VectorParams, Distance
        client = self._get_client()
        try:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )
            logger.info(f"Created Qdrant collection: {name} (dim={dimension})")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection {name}: {e}")
            return False

    def upsert(self, collection: str, points: List[Dict]) -> bool:
        from qdrant_client.models import PointStruct
        client = self._get_client()
        try:
            qdrant_points = [
                PointStruct(id=p.get("id", i), vector=p["embedding"], payload={
                    "text": p["text"],
                    "metadata": p.get("metadata", {}),
                })
                for i, p in enumerate(points)
            ]
            client.upsert(collection_name=collection, points=qdrant_points)
            return True
        except Exception as e:
            logger.error(f"Failed to upsert to {collection}: {e}")
            return False

    def search(self, collection: str, vector: List[float],
               top_k: int = 10) -> List[Dict]:
        client = self._get_client()
        try:
            results = client.search(
                collection_name=collection,
                query_vector=vector,
                limit=top_k,
            )
            return [
                {
                    "id": r.id,
                    "text": r.payload.get("text", ""),
                    "metadata": r.payload.get("metadata", {}),
                    "score": r.score,
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Failed to search {collection}: {e}")
            return []

    def delete_collection(self, name: str) -> bool:
        client = self._get_client()
        try:
            client.delete_collection(collection_name=name)
            return True
        except Exception:
            return False


class InMemoryDB(VectorDB):
    """Simple in-memory vector database (fallback)"""

    def __init__(self):
        self._collections: Dict[str, List[Dict]] = {}
        self._dims: Dict[str, int] = {}

    def create_collection(self, name: str, dimension: int) -> bool:
        self._collections[name] = []
        self._dims[name] = dimension
        return True

    def upsert(self, collection: str, points: List[Dict]) -> bool:
        if collection not in self._collections:
            return False
        self._collections[collection].extend(points)
        return True

    def search(self, collection: str, vector: List[float],
               top_k: int = 10) -> List[Dict]:
        import math
        docs = self._collections.get(collection, [])
        if not docs:
            return []
        q_norm = math.sqrt(sum(x * x for x in vector))
        if q_norm == 0:
            return []
        scored = []
        for doc in docs:
            emb = doc.get("embedding", [])
            e_norm = math.sqrt(sum(x * x for x in emb))
            if e_norm == 0:
                continue
            dot = sum(a * b for a, b in zip(vector, emb))
            score = dot / (q_norm * e_norm)
            scored.append({
                "id": doc.get("id", ""),
                "text": doc.get("text", ""),
                "metadata": doc.get("metadata", {}),
                "score": round(float(score), 4),
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def delete_collection(self, name: str) -> bool:
        return self._collections.pop(name, None) is not None
