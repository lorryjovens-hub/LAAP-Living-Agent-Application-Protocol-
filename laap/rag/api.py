"""
LAAP — RAG API Server

FastAPI server for the RAG service.
"""

from __future__ import annotations
import logging
from typing import List, Optional

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError:
    FastAPI = None
    BaseModel = object

from laap.rag.ingest import DocumentIngestor
from laap.rag.embed import EmbeddingGenerator
from laap.rag.search import SemanticSearcher
from laap.rag.db import InMemoryDB

logger = logging.getLogger("laap.rag.api")

app = FastAPI(title="LAAP RAG Service", version="0.1.0") if FastAPI else None

ingestor = DocumentIngestor()
embedder = EmbeddingGenerator()
searcher = SemanticSearcher()


class IngestRequest(BaseModel):
    text: str
    source: str = "api"
    metadata: Optional[dict] = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    min_score: float = 0.5


class IndexResponse(BaseModel):
    chunks: int
    source: str


class SearchResponse(BaseModel):
    query: str
    results: list
    total: int


if app:

    @app.post("/ingest", response_model=IndexResponse)
    async def ingest_text(req: IngestRequest):
        docs = ingestor.ingest_text(req.text, source=req.source, metadata=req.metadata)
        searcher.index(docs)
        return IndexResponse(chunks=len(docs), source=req.source)

    @app.post("/search", response_model=SearchResponse)
    async def search(req: SearchRequest):
        query_emb = embedder.embed(req.query)
        results = searcher.search(query_emb, top_k=req.top_k, min_score=req.min_score)
        return SearchResponse(query=req.query, results=results, total=len(results))

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "documents": searcher.document_count,
            "embedder": embedder.status,
        }
