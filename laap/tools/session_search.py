"""
LAAP — Session Search Tool
Agent-level FTS5 full-text search across past sessions.
Wraps the existing AoDB search() method with formatted results.
"""
from __future__ import annotations
import json, logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from laap.store.session import AoDB

logger = logging.getLogger("laap.tools.session_search")
_db: Optional[AoDB] = None

def _get_db() -> AoDB:
    global _db
    if _db is None:
        _db = AoDB()
    return _db

def search_sessions(query: str, limit: int = 3) -> str:
    """Search past sessions using FTS5 full-text search."""
    db = _get_db()
    results = db.search_sessions(query, min(limit, 10))
    output = []
    for s in results:
        output.append({
            "session_id": s.get("id", ""),
            "title": s.get("title", ""),
            "source": s.get("source", ""),
            "snippet": s.get("snippet", ""),
            "message_count": s.get("message_count", 0),
        })
    return json.dumps({"results": output, "count": len(output), "query": query})

def search_messages(query: str, session_id: Optional[str] = None, limit: int = 10) -> str:
    """Search messages across sessions (or within one) using FTS5."""
    db = _get_db()
    results = db.search(query, min(limit, 50), session_id=session_id)
    output = []
    for m in results:
        content = m.get("content", "")
        if len(content) > 500:
            content = content[:497] + "..."
        output.append({
            "session_id": m.get("session_id", ""),
            "role": m.get("role", ""),
            "content": content,
            "relevance": m.get("relevance", 0),
        })
    return json.dumps({"results": output, "count": len(output), "query": query})

def get_session(session_id: str, limit: int = 20) -> str:
    """Get messages from a specific session with context."""
    db = _get_db()
    try:
        cur = db._conn.execute(
            """SELECT id, title, source, platform, model, provider,
                      created_at, updated_at, message_count, token_count
               FROM sessions WHERE id=?""", (session_id,))
        session_info = dict(cur.fetchone() or {})
    except Exception:
        session_info = {}
    cur = db._conn.execute(
        """SELECT id, role, content, created_at
           FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?""",
        (session_id, limit))
    messages = [dict(r) for r in cur.fetchall()]
    messages.reverse()
    output = {
        "session": {
            "id": session_id,
            "title": session_info.get("title", ""),
            "source": session_info.get("source", ""),
            "platform": session_info.get("platform", ""),
            "model": session_info.get("model", ""),
            "message_count": session_info.get("message_count", 0),
            "token_count": session_info.get("token_count", 0),
        },
        "messages": [{"id": m.get("id"), "role": m.get("role"),
                       "content": (m.get("content", "")[:1000] + "...")
                       if len(m.get("content", "")) > 1000 else m.get("content", "")}
                      for m in messages],
        "count": len(messages),
    }
    return json.dumps(output)

TOOL_DEFINITIONS = {
    "search_sessions": {
        "name": "search_sessions",
        "description": "Search past sessions using FTS5 full-text search. Returns session titles, snippets, and metadata.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Search query (FTS5 syntax: AND/OR/quoted phrases/wildcards)"},
            "limit": {"type": "integer", "default": 3, "description": "Max sessions to return"}},
            "required": ["query"]},
        "handler": lambda args, **kw: search_sessions(query=args.get("query",""), limit=args.get("limit",3)),
    },
    "search_messages": {
        "name": "search_messages",
        "description": "Search messages across sessions using FTS5. Optionally scope to a single session.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Search query"},
            "session_id": {"type": "string", "description": "Optional session ID to scope search"},
            "limit": {"type": "integer", "default": 10}},
            "required": ["query"]},
        "handler": lambda args, **kw: search_messages(query=args.get("query",""), session_id=args.get("session_id"), limit=args.get("limit",10)),
    },
    "get_session": {
        "name": "get_session",
        "description": "Get messages from a specific session with context (bookends).",
        "parameters": {"type": "object", "properties": {
            "session_id": {"type": "string", "description": "Session ID"},
            "limit": {"type": "integer", "default": 20}},
            "required": ["session_id"]},
        "handler": lambda args, **kw: get_session(session_id=args.get("session_id",""), limit=args.get("limit",20)),
    },
}

def register_tools(registry):
    from laap.tools.base import Tool
    for name, tdef in TOOL_DEFINITIONS.items():
        tool = Tool(name=name, category="search", description=tdef["description"],
                    parameters=tdef["parameters"], handler=tdef["handler"])
        registry.register(tool)
    logger.info("Registered %d session search tools", len(TOOL_DEFINITIONS))
