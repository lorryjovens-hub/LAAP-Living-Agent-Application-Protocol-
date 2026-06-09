"""
LAAP — Session Persistence Manager

Persistent session storage with file and SQLite backends.
Supports session save/restore, compaction, and recovery.
"""

from __future__ import annotations
import json, logging, os, time, threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger("laap.store.session.manager")


class SessionState(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPACTED = "compacted"
    CLOSED = "closed"


@dataclass
class SessionRecord:
    """A persisted session record"""
    session_id: str
    state: SessionState = SessionState.ACTIVE
    turn_count: int = 0
    token_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    parent_id: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)
    summary: str = ""
    tags: List[str] = field(default_factory=list)


class SessionStore:
    """Abstract base for session storage backends"""

    def save(self, session: SessionRecord, messages: List[Dict] = None):
        raise NotImplementedError

    def load(self, session_id: str) -> Optional[SessionRecord]:
        raise NotImplementedError

    def delete(self, session_id: str) -> bool:
        raise NotImplementedError

    def list_sessions(self, limit: int = 50) -> List[SessionRecord]:
        raise NotImplementedError


class FileSessionStore(SessionStore):
    """File-based session storage using JSONL"""

    def __init__(self, storage_dir: str = ""):
        self.storage_dir = storage_dir or os.path.join(
            os.getcwd(), ".laap", "sessions"
        )
        os.makedirs(self.storage_dir, exist_ok=True)
        self._lock = threading.Lock()

    def _session_path(self, session_id: str) -> Path:
        return Path(self.storage_dir) / f"{session_id}.jsonl"

    def _meta_path(self, session_id: str) -> Path:
        return Path(self.storage_dir) / f"{session_id}.meta.json"

    def save(self, session: SessionRecord, messages: List[Dict] = None):
        with self._lock:
            # Save metadata
            meta_path = self._meta_path(session.session_id)
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump({
                    "session_id": session.session_id,
                    "state": session.state.value,
                    "turn_count": session.turn_count,
                    "token_count": session.token_count,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                    "parent_id": session.parent_id,
                    "metadata": session.metadata,
                    "summary": session.summary,
                    "tags": session.tags,
                }, f, ensure_ascii=False, indent=2)

            # Append messages to JSONL
            if messages:
                sess_path = self._session_path(session.session_id)
                with open(sess_path, "a", encoding="utf-8") as f:
                    for msg in messages:
                        f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    def load(self, session_id: str) -> Optional[SessionRecord]:
        meta_path = self._meta_path(session_id)
        if not meta_path.exists():
            return None
        with self._lock:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SessionRecord(
                session_id=data["session_id"],
                state=SessionState(data.get("state", "active")),
                turn_count=data.get("turn_count", 0),
                token_count=data.get("token_count", 0),
                created_at=data.get("created_at", 0),
                updated_at=data.get("updated_at", 0),
                parent_id=data.get("parent_id", ""),
                metadata=data.get("metadata", {}),
                summary=data.get("summary", ""),
                tags=data.get("tags", []),
            )

    def load_messages(self, session_id: str, limit: int = 1000) -> List[Dict]:
        sess_path = self._session_path(session_id)
        if not sess_path.exists():
            return []
        messages = []
        with self._lock:
            with open(sess_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            messages.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
                        if len(messages) >= limit:
                            break
        return messages

    def delete(self, session_id: str) -> bool:
        with self._lock:
            meta_path = self._meta_path(session_id)
            sess_path = self._session_path(session_id)
            deleted = False
            if meta_path.exists():
                meta_path.unlink()
                deleted = True
            if sess_path.exists():
                sess_path.unlink()
                deleted = True
            return deleted

    def list_sessions(self, limit: int = 50) -> List[SessionRecord]:
        sessions = []
        with self._lock:
            for f in sorted(Path(self.storage_dir).glob("*.meta.json"),
                           key=lambda x: x.stat().st_mtime, reverse=True):
                try:
                    with open(f, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    sessions.append(SessionRecord(
                        session_id=data["session_id"],
                        state=SessionState(data.get("state", "active")),
                        turn_count=data.get("turn_count", 0),
                        token_count=data.get("token_count", 0),
                        created_at=data.get("created_at", 0),
                        updated_at=data.get("updated_at", 0),
                        summary=data.get("summary", ""),
                    ))
                except Exception:
                    continue
                if len(sessions) >= limit:
                    break
        return sessions


class SessionManager:
    """Central session management with persistence"""

    def __init__(self, store: Optional[SessionStore] = None):
        self.store = store or FileSessionStore()
        self._active_sessions: Dict[str, SessionRecord] = {}
        self._lock = threading.Lock()

    def create(self, session_id: str, parent_id: str = "",
               metadata: Optional[Dict] = None) -> SessionRecord:
        with self._lock:
            if session_id in self._active_sessions:
                return self._active_sessions[session_id]

            session = SessionRecord(
                session_id=session_id,
                parent_id=parent_id,
                metadata=metadata or {},
            )
            self._active_sessions[session_id] = session
            self.store.save(session)
            logger.info(f"Session created: {session_id}")
            return session

    def get(self, session_id: str) -> Optional[SessionRecord]:
        with self._lock:
            session = self._active_sessions.get(session_id)
            if session:
                return session
        # Try loading from store
        return self.store.load(session_id)

    def save_messages(self, session_id: str, messages: List[Dict]):
        session = self.get(session_id)
        if not session:
            logger.warning(f"Cannot save messages: session {session_id} not found")
            return
        session.turn_count += 1
        session.updated_at = time.time()
        self.store.save(session, messages)

    def compact(self, session_id: str, summary: str):
        """Compact a session by persisting its summary."""
        session = self.get(session_id)
        if session:
            session.state = SessionState.COMPACTED
            session.summary = summary
            self.store.save(session)
            logger.info(f"Session compacted: {session_id}")

    def close(self, session_id: str):
        session = self.get(session_id)
        if session:
            session.state = SessionState.CLOSED
            session.updated_at = time.time()
            self.store.save(session)
            with self._lock:
                self._active_sessions.pop(session_id, None)

    def recover(self, session_id: str) -> Optional[List[Dict]]:
        """Recover a session from storage."""
        if isinstance(self.store, FileSessionStore):
            return self.store.load_messages(session_id)
        return None

    @property
    def status(self) -> dict:
        with self._lock:
            return {
                "active": len(self._active_sessions),
                "total": len([
                    s for s in self.store.list_sessions(999)
                ]),
            }

    # ── Agent State Save/Load ──

    def save_agent_state(self, name: str, agent) -> str:
        """Save agent cognitive state (needs, emotions, config, rewards) to a JSON file.

        Returns the save path.
        """
        save_dir = Path(self.store.storage_dir) / "agent_states"
        save_dir.mkdir(parents=True, exist_ok=True)
        filepath = save_dir / f"{name}.json"

        state = {
            "name": name,
            "agent_name": getattr(getattr(agent, 'config', None), 'name', 'Ao'),
            "step_count": getattr(agent, 'step_count', 0),
            "exploration_rate": getattr(getattr(agent, 'config', None), 'exploration_rate', 0.2),
            "learning_rate": getattr(getattr(agent, 'config', None), 'learning_rate', 0.1),
            "saved_at": time.time(),
            "needs_profile": {},
            "emotional_state": {},
            "reward_history": [],
        }

        # LLM info
        llm = getattr(agent, 'llm', None)
        if llm:
            d = llm.to_dict()
            state["provider"] = d.get("provider", "")
            state["model"] = d.get("model", "")

        # Needs
        if hasattr(agent, 'needs'):
            state["needs_profile"] = {
                nt.value: {
                    "current": agent.needs.needs[nt].current_level,
                    "target": agent.needs.needs[nt].target_level,
                    "decay_rate": agent.needs.needs[nt].decay_rate,
                    "importance": agent.needs.needs[nt].importance,
                }
                for nt in agent.needs.needs
            }

        # Emotions
        if hasattr(agent, 'emotion_gradient'):
            eg = agent.emotion_gradient
            state["emotional_state"] = {
                "valence": eg.state.valence,
                "arousal": eg.state.arousal,
                "dominance": eg.state.dominance,
                "confidence": eg.state.confidence,
            }

        # Reward history
        if hasattr(agent, '_reward_history'):
            state["reward_history"] = agent._reward_history[-200:]

        filepath.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Agent state saved: {name}")
        return str(filepath)

    def load_agent_state(self, name: str, agent) -> bool:
        """Load agent cognitive state from a JSON file.

        Returns True if successful.
        """
        save_dir = Path(self.store.storage_dir) / "agent_states"
        filepath = save_dir / f"{name}.json"
        if not filepath.exists():
            logger.warning(f"Agent state not found: {name}")
            return False

        try:
            state = json.loads(filepath.read_text(encoding="utf-8"))

            # Restore config
            if hasattr(agent, 'config'):
                agent.config.exploration_rate = state.get("exploration_rate", 0.2)
                agent.config.learning_rate = state.get("learning_rate", 0.1)
            agent.step_count = state.get("step_count", 0)

            # Restore needs
            if hasattr(agent, 'needs') and state.get("needs_profile"):
                from laap.cognition.needs import NeedType
                for need_str, data in state["needs_profile"].items():
                    try:
                        nt = NeedType(need_str)
                        if nt in agent.needs.needs:
                            for k, v in data.items():
                                if hasattr(agent.needs.needs[nt], k):
                                    setattr(agent.needs.needs[nt], k, v)
                    except ValueError:
                        pass

            # Restore emotions
            if hasattr(agent, 'emotion_gradient') and state.get("emotional_state"):
                from laap.cognition.emotion import EmotionalState
                es = state["emotional_state"]
                agent.emotion_gradient.state = EmotionalState(
                    valence=es.get("valence", 0.0),
                    arousal=es.get("arousal", 0.5),
                    dominance=es.get("dominance", 0.5),
                    confidence=es.get("confidence", 0.5),
                )

            # Restore reward history
            if hasattr(agent, '_reward_history') and state.get("reward_history"):
                agent._reward_history = list(state["reward_history"])

            logger.info(f"Agent state loaded: {name}")
            return True
        except Exception as e:
            logger.error(f"Agent state load error: {e}")
            return False

    def list_agent_states(self) -> List[dict]:
        """List all saved agent states."""
        save_dir = Path(self.store.storage_dir) / "agent_states"
        if not save_dir.exists():
            return []
        states = []
        for f in sorted(save_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                states.append({
                    "name": f.stem,
                    "agent_name": data.get("agent_name", ""),
                    "step_count": data.get("step_count", 0),
                    "provider": data.get("provider", ""),
                    "model": data.get("model", ""),
                    "saved_at": data.get("saved_at", 0),
                })
            except Exception:
                states.append({"name": f.stem, "error": "corrupt"})
        return states

    def delete_agent_state(self, name: str) -> bool:
        """Delete a saved agent state."""
        save_dir = Path(self.store.storage_dir) / "agent_states"
        filepath = save_dir / f"{name}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False
