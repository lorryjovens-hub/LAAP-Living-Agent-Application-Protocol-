"""
LAAP — Ao Session Store (upgraded with Hermes Agent state.db engine)

SQLite session persistence with:
- WAL mode for concurrent readers + one writer
- FTS5 virtual table for full-text search across messages
- Compression-triggered session splitting via parent_session_id chains
- Session source tagging for multi-platform
- Thread-safe with reentrant locks
"""

from __future__ import annotations
import json
import logging
import sqlite3
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("laap.store.session")

SESSION_DIR = Path.home() / ".laap" / "sessions"
SCHEMA_VERSION = 1


class AoDB:
    """Session database with FTS5 full-text search (Hermes-compatible engine).

    Thread-safe with WAL mode for concurrent access.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (SESSION_DIR / "state.db")
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()

    def _connect(self):
        """Open connection with WAL mode and WAL-compatibility fallback."""
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self):
        """Initialize or migrate database schema."""
        cur = self._conn.cursor()
        cur.executescript(f"""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                parent_id TEXT,
                title TEXT DEFAULT '',
                source TEXT DEFAULT 'cli',
                platform TEXT DEFAULT '',
                model TEXT DEFAULT '',
                provider TEXT DEFAULT '',
                created_at REAL DEFAULT (julianday('now')),
                updated_at REAL DEFAULT (julianday('now')),
                message_count INTEGER DEFAULT 0,
                token_count INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{{}}',
                compressed INTEGER DEFAULT 0,
                FOREIGN KEY (parent_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT DEFAULT '',
                tool_calls TEXT,
                tool_call_id TEXT,
                name TEXT,
                reasoning TEXT,
                created_at REAL DEFAULT (julianday('now')),
                token_count INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS session_tags (
                session_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (session_id, tag),
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
                USING fts5(session_id, role, content, tokenize='unicode61');

            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id, id);

            CREATE INDEX IF NOT EXISTS idx_sessions_updated
                ON sessions(updated_at DESC);

            CREATE INDEX IF NOT EXISTS idx_sessions_source
                ON sessions(source);
        """)

        # Check/migrate schema version
        cur.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = cur.fetchone()
        current_version = row[0] if row else 0

        if current_version < 1:
            cur.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (1)")

        if current_version < SCHEMA_VERSION:
            # Migration: add new columns if needed
            for migration_num in range(current_version + 1, SCHEMA_VERSION + 1):
                self._migrate(migration_num)
            cur.execute(
                "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,)
            )

        self._conn.commit()

    def _migrate(self, target: int):
        """Run migration for target version."""
        cur = self._conn.cursor()
        if target == 2:
            # Already added in schema - skip
            pass

    # ── Session CRUD ───────────────────────────────────────────

    def create_session(self, session_id: Optional[str] = None,
                       parent_id: Optional[str] = None,
                       title: str = "", source: str = "cli",
                       platform: str = "", model: str = "",
                       provider: str = "",
                       metadata: Optional[dict] = None,
                       name: Optional[str] = None) -> str:
        """Create a new session. Returns session ID (or empty string if exists).

        Args:
            session_id: Unique session ID (auto-generated if None)
            name: Alias for title (backward compatible)
        """
        if name and not title:
            title = name
        sid = session_id or str(uuid.uuid4())
        now = time.time()
        with self._lock:
            self._conn.execute(
                """INSERT OR IGNORE INTO sessions
                   (id, parent_id, title, source, platform, model, provider,
                    created_at, updated_at, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (sid, parent_id, title, source, platform, model, provider,
                 now, now, json.dumps(metadata or {}))
            )
            self._conn.commit()
        # Check if this was a new insert or duplicate
        # INSERT OR IGNORE returns no error but doesn't insert if exists
        cur = self._conn.execute("SELECT changes()")
        rows_affected = cur.fetchone()[0]
        if rows_affected == 0:
            logger.debug(f"Session already exists: {sid[:8]}")
            return ""  # Signal duplicate
        logger.debug(f"Session created: {sid[:8]} ({source})")
        return sid

    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session metadata by ID."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            row = cur.fetchone()
            if row:
                d = dict(row)
                # Backward compatible: ensure 'name' key exists (alias for 'title')
                if "name" not in d and "title" in d:
                    d["name"] = d["title"]
                return d
            return None

    def update_session(self, session_id: str, **kwargs):
        """Update session fields (title, model, provider, metadata, etc.)."""
        allowed = {"title", "model", "provider", "source", "platform",
                   "message_count", "token_count", "metadata", "compressed"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        updates["updated_at"] = time.time()

        set_clause = ", ".join(f"{k}=?" for k in updates)
        values = list(updates.values()) + [session_id]

        with self._lock:
            self._conn.execute(
                f"UPDATE sessions SET {set_clause} WHERE id=?", values
            )
            self._conn.commit()

    def list_sessions(self, limit: int = 20, offset: int = 0,
                      source: Optional[str] = None) -> List[dict]:
        """List recent sessions, ordered by last updated."""
        with self._lock:
            if source:
                cur = self._conn.execute(
                    """SELECT id, title, source, platform, model, provider,
                              message_count, created_at, updated_at
                       FROM sessions WHERE source=?
                       ORDER BY updated_at DESC LIMIT ? OFFSET ?""",
                    (source, limit, offset)
                )
            else:
                cur = self._conn.execute(
                    """SELECT id, title, source, platform, model, provider,
                              message_count, created_at, updated_at
                       FROM sessions ORDER BY updated_at DESC LIMIT ? OFFSET ?""",
                    (limit, offset)
                )
            return [dict(r) for r in cur.fetchall()]

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages."""
        with self._lock:
            self._conn.execute("DELETE FROM messages_fts WHERE session_id=?", (session_id,))
            self._conn.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
            self._conn.execute("DELETE FROM session_tags WHERE session_id=?", (session_id,))
            cur = self._conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
            self._conn.commit()
            return cur.rowcount > 0

    # ── Message CRUD ───────────────────────────────────────────

    def add_message(self, session_id: str, role: str, content: str,
                    tool_calls: Optional[list] = None,
                    tool_call_id: Optional[str] = None,
                    name: Optional[str] = None,
                    reasoning: Optional[str] = None,
                    token_count: int = 0) -> int:
        """Add a message to a session. Returns message ID."""
        tcs = json.dumps(tool_calls) if tool_calls else None
        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO messages
                   (session_id, role, content, tool_calls, tool_call_id,
                    name, reasoning, created_at, token_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (session_id, role, content, tcs, tool_call_id,
                 name, reasoning, time.time(), token_count)
            )
            msg_id = cur.lastrowid

            # Update FTS index
            self._conn.execute(
                "INSERT INTO messages_fts (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content)
            )

            # Update session message count
            self._conn.execute(
                """UPDATE sessions SET message_count = message_count + 1,
                        token_count = token_count + ?, updated_at = ?
                   WHERE id = ?""",
                (token_count, time.time(), session_id)
            )
            self._conn.commit()
        return msg_id

    def get_messages(self, session_id: str, limit: int = 100,
                     offset: int = 0) -> List[dict]:
        """Get messages for a session, oldest first."""
        with self._lock:
            cur = self._conn.execute(
                """SELECT id, role, content, tool_calls, tool_call_id,
                          name, reasoning, created_at, token_count
                   FROM messages WHERE session_id=?
                   ORDER BY id ASC LIMIT ? OFFSET ?""",
                (session_id, limit, offset)
            )
            results = []
            for r in cur.fetchall():
                d = dict(r)
                if d["tool_calls"]:
                    try:
                        d["tool_calls"] = json.loads(d["tool_calls"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                results.append(d)
            return results

    def append_message(self, session_id: str, role: str, content: str,
                       tool_calls: Optional[list] = None,
                       tool_call_id: Optional[str] = None,
                       name: Optional[str] = None,
                       reasoning: Optional[str] = None,
                       token_count: int = 0) -> int:
        """Backward compatible: alias for add_message()."""
        return self.add_message(session_id, role, content, tool_calls,
                                tool_call_id, name, reasoning, token_count)

    def get_message_count(self, session_id: str) -> int:
        """Count messages in a session."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id=?", (session_id,)
            )
            return cur.fetchone()[0]

    # ── FTS5 Full-Text Search ──────────────────────────────────

    def search(self, query: str, limit: int = 10,
               session_id: Optional[str] = None) -> List[dict]:
        """Search messages across sessions using FTS5.

        Returns:
            List of dicts with session_id, role, content snippet, rank
        """
        with self._lock:
            if session_id:
                cur = self._conn.execute(
                    """SELECT m.session_id, m.role, m.content,
                              rank as relevance
                       FROM messages_fts f
                       JOIN messages m ON m.id = f.rowid
                       WHERE messages_fts MATCH ? AND f.session_id = ?
                       ORDER BY rank
                       LIMIT ?""",
                    (query, session_id, limit)
                )
            else:
                cur = self._conn.execute(
                    """SELECT m.session_id, m.role, m.content,
                              rank as relevance
                       FROM messages_fts f
                       JOIN messages m ON m.id = f.rowid
                       WHERE messages_fts MATCH ?
                       ORDER BY rank
                       LIMIT ?""",
                    (query, limit)
                )
            return [dict(r) for r in cur.fetchall()]

    def search_sessions(self, query: str, limit: int = 5) -> List[dict]:
        """Search session titles and metadata.

        Returns:
            List of session dicts with relevance scores
        """
        with self._lock:
            cur = self._conn.execute(
                """SELECT s.id, s.title, s.source, s.platform,
                          s.message_count, s.created_at, s.updated_at,
                          snippet(messages_fts, 1, '<b>', '</b>', '...', 32) as snippet
                   FROM sessions s
                   JOIN messages m ON m.session_id = s.id
                   JOIN messages_fts f ON f.rowid = m.id
                   WHERE messages_fts MATCH ?
                   GROUP BY s.id
                   ORDER BY s.updated_at DESC
                   LIMIT ?""",
                (query, limit)
            )
            return [dict(r) for r in cur.fetchall()]

    # ── Tags ───────────────────────────────────────────────────

    def add_tag(self, session_id: str, tag: str):
        """Add a tag to a session."""
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO session_tags (session_id, tag) VALUES (?, ?)",
                (session_id, tag.lower().strip())
            )
            self._conn.commit()

    def remove_tag(self, session_id: str, tag: str):
        """Remove a tag from a session."""
        with self._lock:
            self._conn.execute(
                "DELETE FROM session_tags WHERE session_id=? AND tag=?",
                (session_id, tag.lower().strip())
            )
            self._conn.commit()

    def get_tags(self, session_id: str) -> List[str]:
        """Get all tags for a session."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT tag FROM session_tags WHERE session_id=? ORDER BY tag",
                (session_id,)
            )
            return [r[0] for r in cur.fetchall()]

    # ── Compression / Splitting ────────────────────────────────

    def split_session(self, session_id: str,
                      keep_last: int = 20) -> Optional[str]:
        """Split a session when it grows too large.

        Creates a new child session and moves older messages to it,
        linking via parent_session_id.

        Args:
            session_id: Session to split
            keep_last: Number of most recent messages to keep

        Returns:
            New child session ID, or None if not needed
        """
        total = self.get_message_count(session_id)
        if total <= keep_last + 5:
            return None

        # Create child session
        child_id = self.create_session(
            parent_id=session_id,
            title=f"continuation of {session_id[:8]}",
            source="continuation",
        )

        # Move older messages to child
        with self._lock:
            self._conn.execute(
                """UPDATE messages SET session_id=?
                   WHERE session_id=? AND id NOT IN (
                       SELECT id FROM messages
                       WHERE session_id=?
                       ORDER BY id DESC LIMIT ?
                   )""",
                (child_id, session_id, session_id, keep_last)
            )
            # Update counts
            cur = self._conn.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id=?", (session_id,)
            )
            kept = cur.fetchone()[0]
            self._conn.execute(
                "UPDATE sessions SET message_count=? WHERE id=?", (kept, session_id)
            )
            cur = self._conn.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id=?", (child_id,)
            )
            moved = cur.fetchone()[0]
            self._conn.execute(
                "UPDATE sessions SET message_count=? WHERE id=?", (moved, child_id)
            )
            self._conn.commit()

        logger.info(f"Session {session_id[:8]} split → {child_id[:8]} "
                     f"(kept {kept}, moved {moved})")
        return child_id

    # ── Maintenance ────────────────────────────────────────────

    def vacuum(self):
        """Vacuum the database to reclaim space."""
        with self._lock:
            self._conn.execute("VACUUM")
            logger.info("Database vacuumed")

    def optimize_fts(self):
        """Optimize FTS5 indexes."""
        with self._lock:
            self._conn.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
            logger.info("FTS indexes rebuilt")

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
