"""LAAP — Memory Provider Abstract Base Class

Providers hook into the agent's lifecycle to store and retrieve
persistent memories. Multiple providers can be stacked.
"""

from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger("laap.memory.provider")


class MemoryProvider(ABC):
    """Abstract base for all memory providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider name."""
        ...

    def is_available(self) -> bool:
        """Whether this provider is ready."""
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        """Initialize for a session."""
        pass

    def system_prompt_block(self) -> str:
        """Return text to inject into the system prompt."""
        return ""

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Return relevant memory context for a query."""
        return ""

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """Background prefetch for next turn."""
        pass

    def sync_turn(self, user_content: str, assistant_content: str,
                  *, session_id: str = "", **kwargs) -> None:
        """Store memories from a completed turn."""
        pass

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return tool schemas (remember/recall/forget)."""
        return []

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any],
                         **kwargs) -> str:
        """Handle a memory-related tool call."""
        raise ValueError(f"Unknown tool: {tool_name}")

    def shutdown(self) -> None:
        """Clean up resources."""
        pass

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """Called when a session ends."""
        pass

    def on_delegation(self, task: str, result: str, *,
                      child_session_id: str = "", **kwargs) -> None:
        """Called when a subagent task completes."""
        pass
