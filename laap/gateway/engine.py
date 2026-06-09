"""LAAP Gateway — Core Engine

Session management, message dispatch, streaming bridge between
platform adapters and the LAAP agent.
"""

from __future__ import annotations
import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from laap.gateway.events import (
    MessageChunk, MessageStop, ToolCallChunk, ToolCallResult, GatewayEvent
)

logger = logging.getLogger("laap.gateway.engine")


# ── Session Management ─────────────────────────────────────────

@dataclass
class SessionEntry:
    """A single gateway session."""
    session_id: str
    platform: str
    chat_id: str
    user_id: str
    user_name: str = ""
    chat_name: str = ""
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    message_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


class SessionStore:
    """Thread-safe session storage with JSONL persistence."""

    def __init__(self, sessions_dir: Optional[Path] = None):
        self._dir = sessions_dir or (Path.home() / ".laap" / "sessions")
        self._dir.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, SessionEntry] = {}
        self._transcripts: Dict[str, List[Dict]] = {}
        self._lock = asyncio.Lock()
        self._load()

    def _session_path(self, session_id: str) -> Path:
        return self._dir / f"{session_id}.jsonl"

    def _load(self):
        """Load existing session metadata."""
        meta_path = self._dir / "_sessions.json"
        if meta_path.exists():
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                for s in data:
                    entry = SessionEntry(**s)
                    self._sessions[entry.session_id] = entry
            except (json.JSONDecodeError, OSError):
                pass

    def _save_meta(self):
        """Persist session metadata."""
        meta_path = self._dir / "_sessions.json"
        try:
            data = [s.__dict__ for s in self._sessions.values()]
            meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as e:
            logger.warning(f"Cannot save session meta: {e}")

    async def get_or_create(self, platform: str, chat_id: str, user_id: str,
                            user_name: str = "", chat_name: str = "") -> SessionEntry:
        """Get existing session or create new one."""
        async with self._lock:
            # Find by chat_id + platform
            for s in self._sessions.values():
                if s.platform == platform and s.chat_id == chat_id and s.is_active:
                    s.last_active = time.time()
                    return s

            # Create new
            session_id = str(uuid.uuid4())
            entry = SessionEntry(
                session_id=session_id, platform=platform, chat_id=chat_id,
                user_id=user_id, user_name=user_name, chat_name=chat_name,
            )
            self._sessions[session_id] = entry
            self._transcripts[session_id] = []
            self._save_meta()
            logger.info(f"Session created: {session_id[:8]} ({platform}:{chat_id})")
            return entry

    async def append_message(self, session_id: str, role: str, content: str,
                             tool_calls: Optional[List] = None) -> None:
        """Append a message to the session transcript."""
        async with self._lock:
            transcript = self._transcripts.setdefault(session_id, [])
            msg = {
                "role": role,
                "content": content,
                "timestamp": time.time(),
            }
            if tool_calls:
                msg["tool_calls"] = tool_calls
            transcript.append(msg)

            # Persist to JSONL
            path = self._session_path(session_id)
            try:
                with open(str(path), "a", encoding="utf-8") as f:
                    f.write(json.dumps(msg, ensure_ascii=False) + "\n")
            except OSError as e:
                logger.warning(f"Cannot persist message: {e}")

            if session_id in self._sessions:
                self._sessions[session_id].message_count += 1
                self._sessions[session_id].last_active = time.time()

    async def get_transcript(self, session_id: str) -> List[Dict]:
        """Load full transcript for a session."""
        async with self._lock:
            if session_id in self._transcripts:
                return list(self._transcripts[session_id])

            # Load from disk
            path = self._session_path(session_id)
            messages = []
            if path.exists():
                try:
                    for line in path.read_text(encoding="utf-8").strip().split("\n"):
                        if line.strip():
                            messages.append(json.loads(line))
                except (json.JSONDecodeError, OSError):
                    pass
            self._transcripts[session_id] = messages
            return messages

    async def list_sessions(self, platform: Optional[str] = None,
                            limit: int = 20) -> List[SessionEntry]:
        """List recent sessions."""
        async with self._lock:
            sessions = list(self._sessions.values())
            if platform:
                sessions = [s for s in sessions if s.platform == platform]
            sessions.sort(key=lambda s: s.last_active, reverse=True)
            return sessions[:limit]

    async def close_session(self, session_id: str) -> bool:
        """Mark a session as inactive."""
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].is_active = False
                self._save_meta()
                return True
            return False


# ── Platform Registry ──────────────────────────────────────────

@dataclass
class PlatformInfo:
    """Registered platform adapter info."""
    name: str
    adapter_class: type
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


class PlatformRegistry:
    """Registry for platform adapters."""

    def __init__(self):
        self._platforms: Dict[str, PlatformInfo] = {}

    def register(self, name: str, adapter_class: type,
                 config: Optional[Dict] = None, enabled: bool = True):
        """Register a platform adapter."""
        self._platforms[name] = PlatformInfo(
            name=name, adapter_class=adapter_class,
            config=config or {}, enabled=enabled,
        )
        logger.info(f"Platform registered: {name}")

    def get(self, name: str) -> Optional[PlatformInfo]:
        return self._platforms.get(name)

    def all(self) -> Dict[str, PlatformInfo]:
        return dict(self._platforms)

    def enabled(self) -> Dict[str, PlatformInfo]:
        return {n: p for n, p in self._platforms.items() if p.enabled}


# ── Gateway Engine ─────────────────────────────────────────────

class GatewayEngine:
    """Core gateway engine tying adapters to the LAAP agent."""

    def __init__(self, agent=None):
        self.agent = agent
        self.sessions = SessionStore()
        self.registry = PlatformRegistry()
        self._adapters: Dict[str, Any] = {}
        self._running = False

    def register_platform(self, name: str, adapter_class: type,
                          config: Optional[Dict] = None):
        """Register a platform adapter."""
        self.registry.register(name, adapter_class, config)

    async def start(self):
        """Start all enabled platform adapters."""
        self._running = True
        for name, info in self.registry.enabled().items():
            try:
                adapter = info.adapter_class(
                    config=info.config,
                    engine=self,
                )
                self._adapters[name] = adapter
                asyncio.create_task(adapter.start())
                logger.info(f"Gateway adapter started: {name}")
            except Exception as e:
                logger.error(f"Failed to start {name}: {e}")

    async def stop(self):
        """Stop all adapters."""
        self._running = False
        for name, adapter in self._adapters.items():
            try:
                await adapter.stop()
                logger.info(f"Gateway adapter stopped: {name}")
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")

    async def process_message(self, platform: str, chat_id: str, user_id: str,
                              text: str, user_name: str = "",
                              chat_name: str = "") -> str:
        """Process an incoming message and return the response.

        This is the main entry point - creates/manages sessions,
        calls the agent, and streams back the response.
        """
        # Get or create session
        session = await self.sessions.get_or_create(
            platform=platform, chat_id=chat_id, user_id=user_id,
            user_name=user_name, chat_name=chat_name,
        )
        session_id = session.session_id

        # Record user message
        await self.sessions.append_message(session_id, "user", text)

        # Call agent (if available)
        if self.agent:
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, self.agent.chat, text)
            except Exception as e:
                logger.exception(f"Agent error for session {session_id[:8]}")
                response = f"🐉 Ao encountered an error: {e}"
        else:
            response = f"🐉 LAAP Gateway: Received '{text[:50]}'. Agent not connected."

        # Record assistant message
        await self.sessions.append_message(session_id, "assistant", response)

        return response

    async def broadcast_message(self, platform: str, chat_id: str,
                                 text: str) -> bool:
        """Send a message via a specific platform adapter."""
        adapter = self._adapters.get(platform)
        if adapter and hasattr(adapter, 'send_message'):
            return await adapter.send_message(chat_id, text)
        return False
