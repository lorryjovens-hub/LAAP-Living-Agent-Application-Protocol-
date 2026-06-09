"""
LAAP — Document Chunking

Split documents into optimal chunks for RAG indexing.
Supports multiple chunking strategies.
"""

from __future__ import annotations
import re
from typing import List, Optional


class ChunkStrategy:
    FIXED_SIZE = "fixed_size"
    PARAGRAPH = "paragraph"
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"


class TextChunker:
    """Split text into chunks for embedding and indexing"""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64,
                 strategy: str = "recursive"):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy

    def chunk(self, text: str, metadata: Optional[dict] = None) -> List[dict]:
        """Split text into chunks with metadata."""
        if not text or not text.strip():
            return []

        if self.strategy == ChunkStrategy.FIXED_SIZE:
            chunks = self._fixed_size_chunk(text)
        elif self.strategy == ChunkStrategy.PARAGRAPH:
            chunks = self._paragraph_chunk(text)
        elif self.strategy == ChunkStrategy.RECURSIVE:
            chunks = self._recursive_chunk(text)
        else:
            chunks = self._fixed_size_chunk(text)

        result = []
        for i, chunk_text in enumerate(chunks):
            result.append({
                "text": chunk_text,
                "chunk_index": i,
                "metadata": metadata or {},
            })
        return result

    def _fixed_size_chunk(self, text: str) -> List[str]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk = " ".join(words[i:i + self.chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks

    def _paragraph_chunk(self, text: str) -> List[str]:
        paragraphs = re.split(r"\n\s*\n", text)
        chunks = []
        current = []
        current_len = 0
        for p in paragraphs:
            p_len = len(p.split())
            if current_len + p_len > self.chunk_size and current:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0
            current.append(p)
            current_len += p_len
        if current:
            chunks.append("\n\n".join(current))
        return chunks

    def _recursive_chunk(self, text: str) -> List[str]:
        """Recursive chunking using natural boundaries."""
        if len(text.split()) <= self.chunk_size:
            return [text]

        # Try paragraph split first
        chunks = self._paragraph_chunk(text)
        # If any chunk is still too large, split further
        final = []
        for chunk in chunks:
            if len(chunk.split()) > self.chunk_size:
                final.extend(self._fixed_size_chunk(chunk))
            else:
                final.append(chunk)
        return final

    @property
    def status(self) -> dict:
        return {
            "strategy": self.strategy,
            "chunk_size": self.chunk_size,
            "overlap": self.chunk_overlap,
        }
