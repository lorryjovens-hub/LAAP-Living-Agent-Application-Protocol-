"""LAAP — Memory Manager

Orchestrates multiple memory providers:
- Collects relevant memories for context injection
- Routes memory tool calls to correct provider
- Automatically stores conversation memories
- Background prefetch for performance
"""

from __future__ import annotations
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from laap.memory.provider import MemoryProvider
from laap.memory.persistent import MemoryEntry

logger = logging.getLogger("laap.memory.manager")


class MemoryManager:
    """Orchestrates memory providers for the LAAP agent."""

    def __init__(self):
        self._providers: List[MemoryProvider] = []
        self._tool_map: Dict[str, MemoryProvider] = {}
        self._lock = threading.RLock()
        self._bg_executor: Optional[ThreadPoolExecutor] = None

    def add_provider(self, provider: MemoryProvider) -> None:
        """Register a memory provider."""
        with self._lock:
            self._providers.append(provider)
            # Register tools
            for schema in provider.get_tool_schemas():
                name = schema.get("function", {}).get("name", "")
                if name:
                    self._tool_map[name] = provider
            logger.info(f"Memory provider added: {provider.name}")

    def get_provider(self, name: str) -> Optional[MemoryProvider]:
        """Get a provider by name."""
        for p in self._providers:
            if p.name == name:
                return p
        return None

    # ── Context Building ─────────────────────────────────────

    def build_system_prompt(self) -> str:
        """Collect memory awareness blocks from all providers."""
        blocks = []
        for p in self._providers:
            try:
                block = p.system_prompt_block()
                if block:
                    blocks.append(block)
            except Exception as e:
                logger.debug(f"Memory prompt error [{p.name}]: {e}")
        return "\n".join(blocks)

    def prefetch_all(self, query: str, *, session_id: str = "") -> str:
        """Collect relevant memory context from all providers.

        Returns merged context labeled by provider.
        """
        parts = []
        for p in self._providers:
            try:
                context = p.prefetch(query, session_id=session_id)
                if context:
                    label = f"[{p.name}]"
                    parts.append(f"{label}\n{context}")
            except Exception as e:
                logger.debug(f"Memory prefetch error [{p.name}]: {e}")
        return "\n\n".join(parts)

    def queue_prefetch_all(self, query: str, *, session_id: str = "") -> None:
        """Queue background prefetch for next turn."""
        def _run():
            for p in self._providers:
                try:
                    p.queue_prefetch(query, session_id=session_id)
                except Exception as e:
                    logger.debug(f"Queue prefetch error [{p.name}]: {e}")

        self._submit_background(_run)

    def sync_all(self, user_content: str, assistant_content: str,
                 *, session_id: str = "", **kwargs) -> None:
        """Sync all providers with the latest turn."""
        for p in self._providers:
            try:
                p.sync_turn(user_content, assistant_content,
                           session_id=session_id, **kwargs)
            except Exception as e:
                logger.debug(f"Memory sync error [{p.name}]: {e}")

    # ── Tool Dispatch ────────────────────────────────────────

    def get_all_tool_schemas(self) -> List[Dict[str, Any]]:
        """Collect tool schemas from all providers."""
        schemas = []
        for p in self._providers:
            try:
                schemas.extend(p.get_tool_schemas())
            except Exception as e:
                logger.debug(f"Tool schema error [{p.name}]: {e}")
        return schemas

    def get_all_tool_names(self) -> set:
        """Return set of all memory tool names."""
        return set(self._tool_map.keys())

    def has_tool(self, name: str) -> bool:
        return name in self._tool_map

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any],
                         **kwargs) -> str:
        """Route tool call to the correct provider."""
        provider = self._tool_map.get(tool_name)
        if not provider:
            raise ValueError(f"No provider handles tool: {tool_name}")
        return provider.handle_tool_call(tool_name, args, **kwargs)

    # ── Lifecycle Hooks ──────────────────────────────────────

    def initialize_all(self, session_id: str, **kwargs) -> None:
        """Initialize all providers for a new session."""
        for p in self._providers:
            try:
                p.initialize(session_id, **kwargs)
            except Exception as e:
                logger.warning(f"Memory init error [{p.name}]: {e}")

    def on_turn_start(self, turn_number: int, message: str, **kwargs) -> None:
        """Notify providers of new turn."""
        for p in self._providers:
            try:
                if hasattr(p, 'on_turn_start'):
                    p.on_turn_start(turn_number, message, **kwargs)
            except Exception as e:
                logger.debug(f"Turn start error [{p.name}]: {e}")

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """Notify providers of session end."""
        for p in self._providers:
            try:
                p.on_session_end(messages)
            except Exception as e:
                logger.debug(f"Session end error [{p.name}]: {e}")

    def shutdown_all(self) -> None:
        """Shut down all providers."""
        # Drain background executor
        if self._bg_executor:
            try:
                self._bg_executor.shutdown(wait=True, timeout=5)
            except Exception:
                pass
            self._bg_executor = None

        for p in reversed(self._providers):
            try:
                p.shutdown()
            except Exception as e:
                logger.debug(f"Shutdown error [{p.name}]: {e}")
        logger.info("All memory providers shut down")

    # ── Background Workers ───────────────────────────────────

    def _submit_background(self, fn) -> None:
        """Run fn on background thread."""
        if self._bg_executor is None:
            self._bg_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mem")
        try:
            self._bg_executor.submit(fn)
        except RuntimeError:
            # Executor shut down
            pass
