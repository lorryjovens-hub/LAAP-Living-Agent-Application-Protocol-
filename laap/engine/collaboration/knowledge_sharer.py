"""Knowledge Sharing — 知识共享"""
from __future__ import annotations
import time, json, logging, threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("engine.collaboration.knowledge")

@dataclass
class KnowledgeItem:
    id: str = ""
    topic: str = ""
    content: str = ""
    source: str = ""
    confidence: float = 0.5
    shared_with: Set[str] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)

class SharingPolicy(str, Enum):
    OPEN = "open"
    TRUSTED_ONLY = "trusted_only"
    GROUP = "group"
    PRIVATE = "private"

class KnowledgeSharer:
    def __init__(self, identity: str = ""):
        self.identity = identity
        self._knowledge: Dict[str, KnowledgeItem] = {}
        self._trusted: Set[str] = set()
        self.policy = SharingPolicy.OPEN
        self._lock = threading.RLock()
    def add_knowledge(self, topic: str, content: str, confidence: float = 0.5) -> str:
        item = KnowledgeItem(id=f"kn_{int(time.time()*1e6)}", topic=topic,
                           content=content, source=self.identity, confidence=confidence)
        with self._lock:
            self._knowledge[item.id] = item
        return item.id
    def share(self, item_id: str, target: str) -> bool:
        with self._lock:
            item = self._knowledge.get(item_id)
            if not item:
                return False
            if self.policy == SharingPolicy.TRUSTED_ONLY and target not in self._trusted:
                return False
            item.shared_with.add(target)
            return True
    def query(self, topic: str) -> List[KnowledgeItem]:
        with self._lock:
            return [item for item in self._knowledge.values() if topic.lower() in item.topic.lower()]
    def trust(self, identity: str):
        with self._lock:
            self._trusted.add(identity)
    def get_stats(self) -> dict:
        return {"items": len(self._knowledge), "trusted": len(self._trusted)}
