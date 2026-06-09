"""LAAP — Builtin Memory Provider

SQLite-backed persistent memory provider implementing MemoryProvider ABC.
Automatically stores conversation memories and injects relevant context.
"""

from __future__ import annotations
import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional

from laap.memory.provider import MemoryProvider
from laap.memory.persistent import PersistentMemoryEngine, MemoryEntry

logger = logging.getLogger("laap.memory.builtin")


class BuiltinMemoryProvider(MemoryProvider):
    """Built-in persistent memory provider.

    Features:
    - Auto-stores important facts from conversations
    - Injects relevant memories into system prompt
    - Supports remember/recall/forget/search tools
    - Memory decay (old/unimportant memories fade)
    """

    def __init__(self, db_path=None):
        self._engine = PersistentMemoryEngine(db_path)
        self._lock = threading.Lock()
        self._user_id = "default"
        self._session_id = ""
        self._turn_count = 0

    @property
    def name(self) -> str:
        return "builtin"

    def initialize(self, session_id: str, **kwargs) -> None:
        """Initialize for a new session."""
        self._session_id = session_id
        self._turn_count = 0
        self._user_id = kwargs.get("user_id", "default")

    def system_prompt_block(self) -> str:
        """Return memory awareness block for system prompt."""
        count = self._engine.count(user_id=self._user_id)
        if count == 0:
            return ""
        lines = [
            "",
            "[Memory System]",
            f"You have {count} stored memories. "
            "Use `remember` to store new facts, `recall` to retrieve, "
            "and `forget` to remove. Relevant memories are automatically loaded.",
        ]
        return "\n".join(lines)

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Retrieve relevant memories for a query."""
        results = self._engine.search(query, limit=5, user_id=self._user_id)

        # Also add high-importance memories
        top = self._engine.recall(limit=3, min_importance=0.7, user_id=self._user_id)

        # Merge deduplicated
        seen: set = set()
        combined = []
        for e in results + top:
            if e.id not in seen:
                seen.add(e.id)
                combined.append(e)
                e.record_access()

        if not combined:
            return ""

        blocks = [e.to_prompt_block() for e in combined[:8]]
        header = "\n\U0001F9E0 **Relevant Memories:**"
        return "\n".join(["", header] + blocks)

    def sync_turn(self, user_content: str, assistant_content: str,
                  *, session_id: str = "", **kwargs) -> None:
        """Auto-store important information from a conversation turn."""
        self._turn_count += 1
        if not user_content or not assistant_content:
            return

        # Store as episodic memory (lightweight)
        if len(user_content) > 10:
            self._engine.store(MemoryEntry(
                content=f"User said: {user_content[:200]}",
                memory_type="episode",
                importance=0.3,
                tags=["conversation", "episode"],
                source="conversation",
            ), user_id=self._user_id)

        # Detect potential facts (statements with "I am", "I like", "my", etc.)
        self._extract_facts(user_content)

    def _extract_facts(self, text: str):
        """Extract factual statements from text."""
        patterns = [
            ("I am ", "identity"),
            ("I'm ", "identity"),
            ("my name is ", "identity"),
            ("I like ", "preference"),
            ("I love ", "preference"),
            ("I hate ", "preference"),
            ("I prefer ", "preference"),
            ("I work as ", "fact"),
            ("I work at ", "fact"),
            ("I use ", "fact"),
            ("I have ", "fact"),
            ("I need ", "fact"),
            ("I want ", "fact"),
            ("remember that ", "fact"),
            ("important: ", "fact"),
            ("note: ", "fact"),
            ("fact: ", "fact"),
        ]

        text_lower = text.lower()
        for pattern, mem_type in patterns:
            if pattern in text_lower:
                idx = text_lower.index(pattern)
                end = text.find(".", idx)
                if end < 0:
                    end = min(idx + 150, len(text))
                content = text[idx:end].strip()
                if len(content) > 5:
                    # Check for duplicate
                    existing = self._engine.search(content[:30], limit=1, user_id=self._user_id)
                    if not existing:
                        self._engine.store(MemoryEntry(
                            content=content,
                            memory_type=mem_type,
                            importance=0.6,
                            tags=[mem_type, "auto-extracted"],
                            source="auto-extract",
                        ), user_id=self._user_id)

    # ── Tool Support ─────────────────────────────────────────

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Register memory tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "remember",
                    "description": "Store a fact, preference, or important information in long-term memory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "What to remember"},
                            "type": {
                                "type": "string",
                                "enum": ["fact", "preference", "concept", "skill"],
                                "default": "fact",
                                "description": "Type of memory",
                            },
                            "importance": {
                                "type": "number",
                                "default": 0.5,
                                "description": "Importance 0-1",
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Tags for categorization",
                            },
                        },
                        "required": ["content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "recall",
                    "description": "Recall stored memories, optionally filtered by type or query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "type": {
                                "type": "string",
                                "enum": ["fact", "preference", "episode", "concept", "skill", "identity"],
                                "description": "Filter by memory type",
                            },
                            "limit": {"type": "integer", "default": 5},
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "forget",
                    "description": "Delete a specific memory by its content or ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Content or ID to forget"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "memory_stats",
                    "description": "Get statistics about stored memories",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
        ]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any],
                         **kwargs) -> str:
        """Handle memory tool calls."""
        if tool_name == "remember":
            return self._tool_remember(args)
        elif tool_name == "recall":
            return self._tool_recall(args)
        elif tool_name == "forget":
            return self._tool_forget(args)
        elif tool_name == "memory_stats":
            return self._tool_stats()
        raise ValueError(f"Unknown memory tool: {tool_name}")

    def _tool_remember(self, args: Dict) -> str:
        content = args.get("content", "")
        mem_type = args.get("type", "fact")
        importance = float(args.get("importance", 0.5))
        tags = args.get("tags", [])

        if not content:
            return json.dumps({"error": "No content provided"})

        entry = MemoryEntry(
            content=content, memory_type=mem_type,
            importance=importance, tags=tags,
            source="tool",
        )
        self._engine.store(entry, user_id=self._user_id)
        return json.dumps({
            "status": "stored",
            "id": entry.id[:8],
            "type": mem_type,
            "importance": importance,
        })

    def _tool_recall(self, args: Dict) -> str:
        query = args.get("query", "")
        mem_type = args.get("type")
        limit = int(args.get("limit", 5))

        if query:
            results = self._engine.search(query, limit=limit,
                                          memory_type=mem_type,
                                          user_id=self._user_id)
        elif mem_type:
            results = self._engine.recall_by_type(mem_type, limit=limit,
                                                  user_id=self._user_id)
        else:
            results = self._engine.recall(limit=limit, user_id=self._user_id)

        output = [r.to_dict() for r in results]
        return json.dumps({"memories": output, "count": len(output)})

    def _tool_forget(self, args: Dict) -> str:
        query = args.get("query", "")
        if not query:
            return json.dumps({"error": "No query provided"})

        # Try direct ID match
        if self._engine.delete(query):
            return json.dumps({"status": "deleted", "id": query})

        # Try search + delete first match
        results = self._engine.search(query, limit=1, user_id=self._user_id)
        if results:
            self._engine.delete(results[0].id)
            return json.dumps({"status": "deleted", "content": results[0].content[:60]})

        return json.dumps({"error": "No matching memory found"})

    def _tool_stats(self) -> str:
        stats = self._engine.summarize(user_id=self._user_id)
        return json.dumps(stats)

    # ── Lifecycle ────────────────────────────────────────────

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """Store session summary."""
        if messages:
            summary = f"Conversation with {len(messages)} messages"
            self._engine.store(MemoryEntry(
                content=summary,
                memory_type="episode",
                importance=0.4,
                tags=["session", "conversation"],
                source="session_end",
            ), user_id=self._user_id)

    def shutdown(self) -> None:
        """Close database."""
        self._engine.close()
        logger.info("Builtin memory provider shut down")
