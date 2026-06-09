"""
LAAP — Embedding Generator

Generate embeddings for RAG using multiple backends:
  - sentence-transformers (local)
  - OpenAI embeddings (API)
  - FastEmbed (lightweight Rust-backed)
"""

from __future__ import annotations
import logging, os, time
from typing import List, Optional

logger = logging.getLogger("laap.rag.embed")


class EmbeddingGenerator:
    """Generate vector embeddings for text chunks"""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5",
                 provider: str = "local"):
        self.model_name = model_name
        self.provider = provider
        self._model = None
        self._dimension = 384  # bge-small-en default

    def _load_model(self):
        if self._model is not None:
            return
        if self.provider == "local":
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
                logger.info(f"Loaded embedding model: {self.model_name} (dim={self._dimension})")
            except ImportError:
                logger.warning("sentence-transformers not installed, trying fastembed")
                self._load_fastembed()
        elif self.provider == "openai":
            self._dimension = 1536  # text-embedding-3-small
        else:
            self._load_fastembed()

    def _load_fastembed(self):
        try:
            from fastembed import TextEmbedding
            self._model = TextEmbedding(self.model_name)
            self._dimension = 384
        except ImportError:
            raise ImportError(
                "No embedding backend available. Install: "
                "pip install sentence-transformers  or  pip install fastembed"
            )

    def embed(self, text: str) -> List[float]:
        """Embed a single text string."""
        self._load_model()
        if self.provider == "openai":
            return self._embed_openai(text)
        if hasattr(self._model, "encode"):
            result = self._model.encode(text)
            if hasattr(result, "tolist"):
                return result.tolist()
            return list(result)
        # FastEmbed returns iterable
        return list(next(self._model.embed(text)))

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Embed multiple texts in batch."""
        self._load_model()
        if self.provider == "openai":
            return [self._embed_openai(t) for t in texts]
        if hasattr(self._model, "encode"):
            results = self._model.encode(texts, batch_size=batch_size)
            if hasattr(results, "tolist"):
                return results.tolist()
            return [list(r) for r in results]
        return [list(e) for e in self._model.embed(texts)]

    def _embed_openai(self, text: str) -> List[float]:
        import httpx
        api_key = os.environ.get("OPENAI_API_KEY", "")
        resp = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "text-embedding-3-small", "input": text},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def status(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model_name,
            "dimension": self._dimension,
            "loaded": self._model is not None,
        }
