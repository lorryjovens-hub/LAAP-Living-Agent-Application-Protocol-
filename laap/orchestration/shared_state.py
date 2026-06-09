"""
LAAP — 共享状态总线

基于 "PSI: Shared State as the Missing Layer" (Wang et al., 2026)。
多 Agent 通过统一的状态总线协调。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime


@dataclass
class StateSnapshot:
    source_id: str; source_name: str
    tags: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    available_actions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    version: int = 1

    def context_summary(self) -> str:
        parts = [f"[{self.source_name}]"]
        for k, v in self.data.items():
            parts.append(f"  {k}: {v}")
        if self.available_actions:
            parts.append(f"  actions: {', '.join(self.available_actions[:5])}")
        return "\n".join(parts)


class SharedStateBus:
    """共享状态总线"""

    def __init__(self):
        self.snapshots: Dict[str, StateSnapshot] = {}
        self._history: List[StateSnapshot] = []
        self._max_history = 1000
        self._callbacks: Dict[str, List[Callable]] = {}

    def register(self, source_id: str, source_name: str):
        if source_id not in self.snapshots:
            self.snapshots[source_id] = StateSnapshot(
                source_id=source_id, source_name=source_name,
            )

    def publish(self, source_id: str, data: Dict[str, Any],
                tags: Optional[List[str]] = None,
                actions: Optional[List[str]] = None):
        snap = self.snapshots.get(source_id)
        if not snap:
            return
        snap.data = data
        snap.timestamp = datetime.now()
        snap.version += 1
        if tags:
            snap.tags = list(set(snap.tags + tags))
        if actions is not None:
            snap.available_actions = actions
        self._history.append(snap)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        self._trigger(source_id, data)

    def get_context(self) -> str:
        summaries = []
        for snap in self.snapshots.values():
            s = snap.context_summary()
            if s.strip():
                summaries.append(s)
        return "\n---\n".join(summaries)

    def query(self, tags: Optional[List[str]] = None) -> List[StateSnapshot]:
        if not tags:
            return list(self.snapshots.values())
        return [s for s in self.snapshots.values()
                if any(t in s.tags for t in tags)]

    def subscribe(self, source_id: str, cb: Callable):
        self._callbacks.setdefault(source_id, []).append(cb)

    def _trigger(self, source_id: str, data: dict):
        for cb in self._callbacks.get(source_id, []):
            try:
                cb(data)
            except Exception:
                pass

    def status(self) -> dict:
        return {
            "sources": len(self.snapshots),
            "updates": len(self._history),
            "sources_list": [
                {"id": sid, "name": s.source_name, "version": s.version,
                 "tags": s.tags, "keys": list(s.data.keys()),
                 "actions": s.available_actions}
                for sid, s in self.snapshots.items()
            ],
        }
