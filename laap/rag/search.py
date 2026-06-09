"""
LAAP — Semantic Search

Search indexed documents using vector similarity.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("laap.rag.search")


class SemanticSearcher:
    """Semantic search over indexed documents"""

    def __init__(self):
        self._documents: List[Dict] = []
        self._index_built = False

    def index(self, documents: List[Dict]):
        """Index a batch of documents with embeddings."""
        self._documents = documents
        self._index_built = True
        logger.info(f"Indexed {len(documents)} documents for search")

    def search(self, query_embedding: List[float], top_k: int = 5,
               min_score: float = 0.5) -> List[Dict]:
        """Search for similar documents using cosine similarity."""
        if not self._documents:
            return []

        import math
        results = []
        q_norm = math.sqrt(sum(x * x for x in query_embedding))
        if q_norm == 0:
            return []

        for doc in self._documents:
            emb = doc.get("embedding")
            if not emb:
                continue
            e_norm = math.sqrt(sum(x * x for x in emb))
            if e_norm == 0:
                continue

            dot = sum(a * b for a, b in zip(query_embedding, emb))
            score = dot / (q_norm * e_norm)

            if score >= min_score:
                results.append({
                    "text": doc["text"],
                    "metadata": doc.get("metadata", {}),
                    "score": round(float(score), 4),
                    "id": doc.get("id", ""),
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def hybrid_search(self, query_embedding: List[float],
                      keyword: str = "", top_k: int = 5) -> List[Dict]:
        """Hybrid search combining vector + keyword matching."""
        results = self.search(query_embedding, top_k=top_k * 2)

        if keyword:
            keyword_lower = keyword.lower()
            keyword_results = [
                r for r in results
                if keyword_lower in r["text"].lower()
            ]
            # Boost keyword matches
            for r in keyword_results:
                r["score"] = min(1.0, r["score"] * 1.2)
            results.sort(key=lambda x: x["score"], reverse=True)

        return results[:top_k]

    def clear(self):
        self._documents = []
        self._index_built = False

    @property
    def document_count(self) -> int:
        return len(self._documents)

    @property
    def status(self) -> dict:
        return {
            "indexed": self._index_built,
            "document_count": self.document_count,
        }
