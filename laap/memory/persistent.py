"""LAAP — Persistent Memory Engine

SQLite-backed persistent memory with:
- Key-value memory store (user facts, preferences)
- Semantic memory (embedding-based similarity search)
- FTS5 full-text search across all memories
- Memory decay (Ebbinghaus forgetting curve)
- Importance scoring (recency, relevance, significance)
"""

from __future__ import annotations
import hashlib
import json
import logging
import math
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from laap.memory.provider import MemoryProvider

logger = logging.getLogger("laap.memory.persistent")


# ── Memory Types ───────────────────────────────────────────────

MEMORY_TYPES = ["fact", "preference", "episode", "concept", "skill", "identity"]

# Ebbinghaus forgetting curve: recall_prob = e^(-days / decay_constant)
_DECAY_CONSTANT = 7.0  # 7 days to ~37% recall


class MemoryEntry:
    """A single memory entry."""

    def __init__(self, id: str = "", content: str = "",
                 memory_type: str = "fact",
                 importance: float = 0.5,
                 tags: Optional[List[str]] = None,
                 source: str = "user",
                 created_at: Optional[float] = None,
                 accessed_at: Optional[float] = None,
                 access_count: int = 0,
                 embedding: Optional[List[float]] = None,
                 metadata: Optional[Dict] = None):
        self.id = id or str(uuid.uuid4())
        self.content = content
        self.memory_type = memory_type
        self.importance = importance
        self.tags = tags or []
        self.source = source
        self.created_at = created_at or time.time()
        self.accessed_at = accessed_at or time.time()
        self.access_count = access_count
        self.embedding = embedding
        self.metadata = metadata or {}

    @property
    def age_days(self) -> float:
        return (time.time() - self.created_at) / 86400.0

    @property
    def recall_probability(self) -> float:
        """Ebbinghaus forgetting curve."""
        return math.exp(-self.age_days / _DECAY_CONSTANT)

    @property
    def relevance_score(self) -> float:
        """Composite relevance score (0-1)."""
        recency = math.exp(-self.age_days / 30.0)  # 30-day half-life
        frequency = min(1.0, self.access_count / 10.0)
        return 0.4 * self.importance + 0.3 * recency + 0.2 * frequency + 0.1 * self.recall_probability

    def record_access(self):
        """Record an access to this memory."""
        self.access_count += 1
        self.accessed_at = time.time()

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content[:200],
            "type": self.memory_type,
            "importance": round(self.importance, 2),
            "relevance": round(self.relevance_score, 2),
            "tags": self.tags,
            "source": self.source,
            "age_days": round(self.age_days, 1),
            "access_count": self.access_count,
        }

    def to_prompt_block(self) -> str:
        """Format for system prompt injection."""
        tag_str = f" [{', '.join(self.tags)}]" if self.tags else ""
        return f"- [{self.memory_type}]✨ {self.content}{tag_str}"

    @classmethod
    def from_db_row(cls, row: sqlite3.Row) -> "MemoryEntry":
        return cls(
            id=row["id"],
            content=row["content"],
            memory_type=row["type"],
            importance=row["importance"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            source=row["source"],
            created_at=row["created_at"],
            accessed_at=row["accessed_at"],
            access_count=row["access_count"],
            embedding=None,  # Loaded separately if needed
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )


class PersistentMemoryEngine:
    """SQLite-backed persistent memory storage with FTS5 search.

    Thread-safe. Each profile/user gets an isolated database.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or (Path.home() / ".laap" / "memory.db")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()

    def _connect(self):
        """Open connection and initialize schema."""
        self._conn = sqlite3.connect(
            str(self._db_path), check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self):
        """Create tables if needed."""
        cur = self._conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'fact',
                importance REAL DEFAULT 0.5,
                tags TEXT DEFAULT '[]',
                source TEXT DEFAULT 'user',
                created_at REAL NOT NULL,
                accessed_at REAL NOT NULL,
                access_count INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                user_id TEXT DEFAULT 'default'
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
                USING fts5(content, type, tags, tokenize='unicode61');

            CREATE INDEX IF NOT EXISTS idx_memories_type
                ON memories(type, importance DESC);

            CREATE INDEX IF NOT EXISTS idx_memories_user
                ON memories(user_id, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_memories_accessed
                ON memories(accessed_at DESC);
        """)
        self._conn.commit()

    # ── CRUD Operations ──────────────────────────────────────

    def store(self, entry: MemoryEntry, user_id: str = "default") -> str:
        """Store a memory entry. Returns its ID."""
        with self._lock:
            self._conn.execute(
                """INSERT OR REPLACE INTO memories
                   (id, content, type, importance, tags, source,
                    created_at, accessed_at, access_count, metadata, user_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (entry.id, entry.content, entry.memory_type, entry.importance,
                 json.dumps(entry.tags), entry.source,
                 entry.created_at, entry.accessed_at, entry.access_count,
                 json.dumps(entry.metadata), user_id)
            )
            # Update FTS index - find the matching rowid
            cur2 = self._conn.execute("SELECT rowid FROM memories WHERE id = ?", (entry.id,))
            row = cur2.fetchone()
            if row:
                self._conn.execute(
                    "INSERT OR REPLACE INTO memories_fts (rowid, content, type, tags) VALUES (?, ?, ?, ?)",
                    (row[0], entry.content, entry.memory_type, json.dumps(entry.tags))
                )
            self._conn.commit()
        logger.debug(f"Stored memory: {entry.id[:8]} ({entry.memory_type})")
        return entry.id

    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get a memory by ID."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            )
            row = cur.fetchone()
            if row:
                entry = MemoryEntry.from_db_row(row)
                # Increment access
                self._conn.execute(
                    "UPDATE memories SET access_count = access_count + 1, accessed_at = ? WHERE id = ?",
                    (time.time(), memory_id)
                )
                self._conn.commit()
                return entry
        return None

    def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM memories WHERE id = ?", (memory_id,)
            )
            self._conn.commit()
            return cur.rowcount > 0

    # ── Search / Retrieval ───────────────────────────────────

    def search(self, query: str, limit: int = 10,
               memory_type: Optional[str] = None,
               user_id: str = "default") -> List[MemoryEntry]:
        """Full-text search across memories.

        Uses FTS5 ranking. Optionally filter by type.
        """
        with self._lock:
            sql = """
                SELECT m.* FROM memories m
                JOIN memories_fts f ON f.rowid = m.rowid
                WHERE memories_fts MATCH ?
            """
            params = [query]

            if memory_type:
                sql += " AND m.type = ?"
                params.append(memory_type)

            if user_id:
                sql += " AND m.user_id = ?"
                params.append(user_id)

            sql += " ORDER BY rank LIMIT ?"
            params.append(limit)

            cur = self._conn.execute(sql, params)
            return [MemoryEntry.from_db_row(row) for row in cur.fetchall()]

    def recall(self, limit: int = 10, memory_type: Optional[str] = None,
               min_importance: float = 0.0, user_id: str = "default") -> List[MemoryEntry]:
        """Recall most relevant memories by composite score.

        Uses relevance_score which combines:
        - importance (40%)
        - recency (30%)
        - access frequency (20%)
        - recall probability (10%)
        """
        with self._lock:
            sql = "SELECT * FROM memories WHERE user_id = ? AND importance >= ?"
            params = [user_id, min_importance]

            if memory_type:
                sql += " AND type = ?"
                params.append(memory_type)

            sql += " ORDER BY accessed_at DESC, importance DESC LIMIT ?"
            params.append(limit)

            cur = self._conn.execute(sql, params)
            entries = [MemoryEntry.from_db_row(row) for row in cur.fetchall()]

            # Sort by composite relevance
            entries.sort(key=lambda e: e.relevance_score, reverse=True)
            return entries[:limit]

    def recall_by_type(self, memory_type: str, limit: int = 10,
                       user_id: str = "default") -> List[MemoryEntry]:
        """Recall memories of a specific type."""
        return self.recall(limit=limit, memory_type=memory_type, user_id=user_id)

    def search_by_tags(self, tags: List[str], limit: int = 20,
                       user_id: str = "default") -> List[MemoryEntry]:
        """Find memories with specific tags."""
        with self._lock:
            results = []
            for tag in tags:
                cur = self._conn.execute(
                    """SELECT * FROM memories
                       WHERE user_id = ? AND tags LIKE ?
                       ORDER BY importance DESC LIMIT ?""",
                    (user_id, f'%{tag}%', limit)
                )
                results.extend(MemoryEntry.from_db_row(r) for r in cur.fetchall())
            # Deduplicate by ID
            seen: Set[str] = set()
            unique = []
            for e in results:
                if e.id not in seen:
                    seen.add(e.id)
                    unique.append(e)
            unique.sort(key=lambda e: e.relevance_score, reverse=True)
            return unique[:limit]

    def count(self, user_id: str = "default",
              memory_type: Optional[str] = None) -> int:
        """Count memories."""
        with self._lock:
            sql = "SELECT COUNT(*) FROM memories WHERE user_id = ?"
            params = [user_id]
            if memory_type:
                sql += " AND type = ?"
                params.append(memory_type)
            cur = self._conn.execute(sql, params)
            return cur.fetchone()[0]

    # ── Maintenance ──────────────────────────────────────────

    def decay(self, threshold_days: float = 90.0,
              user_id: str = "default") -> int:
        """Remove memories below importance threshold after long inactivity.

        Returns number of memories removed.
        """
        cutoff = time.time() - (threshold_days * 86400)
        with self._lock:
            cur = self._conn.execute(
                """DELETE FROM memories
                   WHERE user_id = ? AND importance < 0.3 AND accessed_at < ?""",
                (user_id, cutoff)
            )
            removed = cur.rowcount
            if removed:
                self._conn.commit()
                logger.info(f"Decay removed {removed} old memories")
            return removed

    def summarize(self, user_id: str = "default") -> Dict:
        """Get memory statistics."""
        return {
            "total": self.count(user_id=user_id),
            "by_type": {
                t: self.count(user_id=user_id, memory_type=t)
                for t in MEMORY_TYPES
            },
            "db_path": str(self._db_path),
        }

    def close(self):
        """Close the database."""
        if self._conn:
            self._conn.close()
            self._conn = None
