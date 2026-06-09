"""Tests for LAAP RAG Service"""
import pytest
from laap.rag.chunk import TextChunker, ChunkStrategy
from laap.rag.search import SemanticSearcher
from laap.rag.db import InMemoryDB


class TestTextChunker:
    def test_fixed_size_chunk(self):
        chunker = TextChunker(chunk_size=10, chunk_overlap=2, strategy="fixed_size")
        text = "word " * 25
        chunks = chunker.chunk(text)
        assert len(chunks) > 1

    def test_paragraph_chunk(self):
        chunker = TextChunker(strategy="paragraph")
        text = "Para one.\n\nPara two.\n\nPara three."
        chunks = chunker.chunk(text)
        assert len(chunks) >= 1

    def test_recursive_chunk(self):
        chunker = TextChunker(chunk_size=20, chunk_overlap=5, strategy="recursive")
        text = "word " * 50
        chunks = chunker.chunk(text)
        assert len(chunks) > 1

    def test_empty_text(self):
        chunker = TextChunker()
        chunks = chunker.chunk("")
        assert len(chunks) == 0

    def test_metadata_preserved(self):
        chunker = TextChunker()
        chunks = chunker.chunk("Hello world", metadata={"source": "test"})
        assert chunks[0]["metadata"]["source"] == "test"


class TestSemanticSearcher:
    def test_empty_search(self):
        searcher = SemanticSearcher()
        results = searcher.search([0.1, 0.2, 0.3])
        assert results == []

    def test_index_and_search(self):
        searcher = SemanticSearcher()
        docs = [
            {"id": "1", "text": "hello world", "embedding": [1.0, 0.0, 0.0], "metadata": {}},
            {"id": "2", "text": "goodbye world", "embedding": [0.0, 1.0, 0.0], "metadata": {}},
        ]
        searcher.index(docs)
        results = searcher.search([1.0, 0.0, 0.0], top_k=5, min_score=0.0)
        assert len(results) > 0
        assert results[0]["id"] == "1"

    def test_clear(self):
        searcher = SemanticSearcher()
        searcher.index([{"id": "1", "text": "test", "embedding": [1.0], "metadata": {}}])
        searcher.clear()
        assert searcher.document_count == 0

    def test_status(self):
        searcher = SemanticSearcher()
        status = searcher.status
        assert "indexed" in status


class TestInMemoryDB:
    def test_create_and_search(self):
        db = InMemoryDB()
        db.create_collection("test", dimension=3)
        db.upsert("test", [
            {"id": "1", "text": "hello", "embedding": [1.0, 0.0, 0.0], "metadata": {}},
        ])
        results = db.search("test", [1.0, 0.0, 0.0])
        assert len(results) == 1

    def test_delete(self):
        db = InMemoryDB()
        db.create_collection("temp", dimension=2)
        assert db.delete_collection("temp")
        assert not db.delete_collection("nonexistent")
