"""
LAAP — Document Ingestor

Ingest documents into the RAG pipeline:
  text → chunk → embed → index
"""

from __future__ import annotations
import logging, os, time
from pathlib import Path
from typing import Dict, List, Optional, Generator

from laap.rag.chunk import TextChunker
from laap.rag.embed import EmbeddingGenerator

logger = logging.getLogger("laap.rag.ingest")


class DocumentIngestor:
    """Ingest documents into vector index"""

    def __init__(self, chunker: Optional[TextChunker] = None,
                 embedder: Optional[EmbeddingGenerator] = None):
        self.chunker = chunker or TextChunker()
        self.embedder = embedder or EmbeddingGenerator()
        self._stats = {"ingested": 0, "failed": 0, "total_chunks": 0}

    def ingest_text(self, text: str, source: str = "memory",
                    metadata: Optional[Dict] = None) -> List[Dict]:
        """Ingest a text document."""
        chunks = self.chunker.chunk(text, metadata={"source": source, **(metadata or {})})
        embeddings = self.embedder.embed_batch([c["text"] for c in chunks])

        documents = []
        for chunk, embedding in zip(chunks, embeddings):
            documents.append({
                "id": f"{source}_{self._stats['total_chunks']}",
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "embedding": embedding,
                "chunk_index": chunk["chunk_index"],
            })
            self._stats["total_chunks"] += 1

        self._stats["ingested"] += 1
        logger.info(f"Ingested {len(documents)} chunks from '{source}'")
        return documents

    def ingest_file(self, file_path: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """Ingest a file document."""
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            self._stats["failed"] += 1
            return []

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            return self.ingest_text(
                text, source=str(path),
                metadata={"filename": path.name, "path": str(path), **(metadata or {})},
            )
        except Exception as e:
            logger.error(f"Failed to ingest {file_path}: {e}")
            self._stats["failed"] += 1
            return []

    def ingest_directory(self, dir_path: str, pattern: str = "*.py",
                         recursive: bool = True) -> List[Dict]:
        """Ingest all matching files in a directory."""
        path = Path(dir_path)
        if not path.is_dir():
            logger.error(f"Directory not found: {dir_path}")
            return []

        all_docs = []
        glob_pattern = f"**/{pattern}" if recursive else pattern
        for file_path in sorted(path.glob(glob_pattern)):
            docs = self.ingest_file(str(file_path))
            all_docs.extend(docs)

        logger.info(f"Ingested {len(all_docs)} total chunks from {dir_path}")
        return all_docs

    @property
    def stats(self) -> dict:
        return {**self._stats}
