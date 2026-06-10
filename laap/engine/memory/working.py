"""
LAAP Memory Engine — Working Memory (工作记忆)
Based on Baddeley's Working Memory Model:
- Central Executive: Attention control
- Phonological Loop: Verbal information
- Visuospatial Sketchpad: Visual/Spatial info
- Episodic Buffer: Integration
"""

from __future__ import annotations
import time
import json
import logging
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("engine.memory.working")

CAPACITY_LIMIT = 7  # Miller's Law: 7±2 chunks
DEFAULT_TTL_SECONDS = 300  # 5 minutes


class ChunkType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    CONCEPT = "concept"
    RELATION = "relation"
    ACTION = "action"
    GOAL = "goal"
    EMOTION = "emotion"
    QUERY = "query"
    RESPONSE = "response"


@dataclass
class WorkingMemoryChunk:
    id: str
    content: Any
    chunk_type: ChunkType = ChunkType.TEXT
    created_at: float = field(default_factory=time.time)
    last_access: float = field(default_factory=time.time)
    access_count: int = 1
    ttl: float = DEFAULT_TTL_SECONDS
    attention_weight: float = 0.5
    source: str = ""
    metadata: Dict = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        return (time.time() - self.last_access) > self.ttl
    
    def touch(self):
        self.last_access = time.time()
        self.access_count += 1
    
    def to_dict(self) -> dict:
        return {
            "id": self.id, "content": str(self.content)[:100],
            "type": self.chunk_type.value, "created_at": self.created_at,
            "last_access": self.last_access, "access_count": self.access_count,
            "ttl": self.ttl, "attention_weight": self.attention_weight,
        }


class ChunkStore:
    """工作记忆存储 - OrderedDict with capacity limit"""
    
    def __init__(self, capacity: int = CAPACITY_LIMIT):
        self._chunks: OrderedDict[str, WorkingMemoryChunk] = OrderedDict()
        self.capacity = capacity
    
    def add(self, chunk: WorkingMemoryChunk) -> bool:
        if chunk.id in self._chunks:
            self._chunks[chunk.id].touch()
            return False
        if len(self._chunks) >= self.capacity:
            self._evict_one()
        self._chunks[chunk.id] = chunk
        return True
    
    def get(self, chunk_id: str) -> Optional[WorkingMemoryChunk]:
        chunk = self._chunks.get(chunk_id)
        if chunk:
            chunk.touch()
            self._chunks.move_to_end(chunk_id)
        return chunk
    
    def remove(self, chunk_id: str) -> bool:
        if chunk_id in self._chunks:
            del self._chunks[chunk_id]
            return True
        return False
    
    def _evict_one(self):
        if not self._chunks:
            return
        candidates = sorted(self._chunks.values(), key=lambda c: (c.attention_weight, c.last_access))
        evict = candidates[0]
        del self._chunks[evict.id]
        logger.debug(f"Evicted chunk: {evict.id} (weight={evict.attention_weight})")
    
    def clear(self):
        self._chunks.clear()
    
    def get_all(self) -> List[WorkingMemoryChunk]:
        return list(self._chunks.values())
    
    def get_by_type(self, chunk_type: ChunkType) -> List[WorkingMemoryChunk]:
        return [c for c in self._chunks.values() if c.chunk_type == chunk_type]
    
    def size(self) -> int:
        return len(self._chunks)
    
    def cleanup_expired(self) -> int:
        expired = [cid for cid, c in self._chunks.items() if c.is_expired()]
        for cid in expired:
            del self._chunks[cid]
        return len(expired)


class WorkingMemory:
    """工作记忆主类 - Baddeley模型实现"""
    
    def __init__(self, capacity: int = CAPACITY_LIMIT, ttl: float = DEFAULT_TTL_SECONDS):
        self._store = ChunkStore(capacity)
        self.default_ttl = ttl
        self._rehearsal_count: Dict[str, int] = {}
        self._chunking_groups: Dict[str, List[str]] = {}
        self._lock = threading.RLock()
    
    def store(self, content: Any, chunk_type: ChunkType = ChunkType.TEXT,
              attention_weight: float = 0.5, source: str = "",
              metadata: Dict = None) -> WorkingMemoryChunk:
        chunk_id = f"wm_{int(time.time() * 1e6)}_{hash(str(content)) % 10000}"
        chunk = WorkingMemoryChunk(
            id=chunk_id, content=content, chunk_type=chunk_type,
            ttl=self.default_ttl, attention_weight=attention_weight,
            source=source, metadata=metadata or {}
        )
        with self._lock:
            self._store.add(chunk)
        return chunk
    
    def recall(self, chunk_id: str) -> Optional[Any]:
        chunk = self._store.get(chunk_id)
        if chunk:
            self._rehearsal_count[chunk_id] = self._rehearsal_count.get(chunk_id, 0) + 1
            return chunk.content
        return None
    
    def update_attention(self, chunk_id: str, new_weight: float):
        chunk = self._store.get(chunk_id)
        if chunk:
            chunk.attention_weight = max(0.0, min(1.0, new_weight))
    
    def get_context(self) -> str:
        chunks = self._store.get_all()
        parts = []
        for c in sorted(chunks, key=lambda x: x.attention_weight, reverse=True):
            content_str = str(c.content)[:200]
            parts.append(f"[{c.chunk_type.value}] {content_str}")
        return "\n".join(parts)
    
    def rehearse(self, chunk_id: str) -> bool:
        chunk = self._store.get(chunk_id)
        if chunk:
            chunk.touch()
            self._rehearsal_count[chunk_id] = self._rehearsal_count.get(chunk_id, 0) + 1
            return True
        return False
    
    def chunk(self, chunk_ids, group_id):
        chunks = [self._store.get(cid) for cid in chunk_ids if self._store.get(cid)]
        if not chunks:
            return None
        combined = " | ".join(str(c.content) for c in chunks)
        import uuid
        new_id = f"wm_{int(time.time()*1e6)}_{uuid.uuid4().hex[:6]}"
        new_chunk = WorkingMemoryChunk(id=new_id, content=combined, chunk_type=ChunkType.CONCEPT, source="chunking")
        self._store.add(new_chunk)
        self._chunking_groups[new_id] = list(chunk_ids)
        for cid in chunk_ids:
            self._store.remove(cid)
        return new_chunk
    def dechunk(self, chunk_id: str) -> List[WorkingMemoryChunk]:
        group = self._chunking_groups.pop(chunk_id, [])
        self._store.remove(chunk_id)
        return [self._store.get(cid) for cid in group if self._store.get(cid)]
    
    def get_active(self) -> List[WorkingMemoryChunk]:
        return [c for c in self._store.get_all() if c.attention_weight > 0.3]
    
    def cleanup(self) -> int:
        with self._lock:
            return self._store.cleanup_expired()
    
    def get_stats(self) -> dict:
        chunks = self._store.get_all()
        return {
            "size": len(chunks),
            "capacity": self._store.capacity,
            "types": {t.value: len(self.store.get_by_type(t)) for t in ChunkType},
            "avg_attention": sum(c.attention_weight for c in chunks) / max(len(chunks), 1),
            "total_rehearsals": sum(self._rehearsal_count.values()),
        }
    
    def serialize(self) -> dict:
        return {
            "chunks": [c.to_dict() for c in self._store.get_all()],
            "chunking_groups": self._chunking_groups,
        }


class ContextManager:
    """上下文管理器 - 管理当前会话上下文"""
    
    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self._history: List[Dict] = []
        self._current_context: Dict = {}
    
    def push(self, entry: Dict):
        self._history.append({
            "timestamp": time.time(),
            **entry
        })
        if len(self._history) > self.window_size * 2:
            self._history = self._history[-self.window_size:]
        self._current_context.update(entry)
    
    def get_recent(self, n: int = 5) -> List[Dict]:
        return self._history[-n:]
    
    def get_context_snapshot(self) -> Dict:
        return {
            "current": self._current_context,
            "history_depth": len(self._history),
            "window_size": self.window_size,
        }
    
    def clear(self):
        self._history.clear()
        self._current_context.clear()


class AttentionFilter:
    """注意力筛选器 - 决定哪些信息进入工作记忆"""
    
    def __init__(self):
        self._thresholds = {
            "urgency": 0.3,
            "relevance": 0.4,
            "novelty": 0.2,
        }
    
    def should_attend(self, item: Dict) -> Tuple[bool, float]:
        score = 0.0
        score += item.get("urgency", 0) * 0.4
        score += item.get("relevance", 0) * 0.35
        score += item.get("novelty", 0) * 0.15
        score += item.get("emotional_salience", 0) * 0.1
        return score >= sum(self._thresholds.values()) / 3, score
    
    def filter(self, items: List[Dict]) -> List[Tuple[Dict, float]]:
        results = []
        for item in items:
            attend, score = self.should_attend(item)
            if attend:
                results.append((item, score))
        return sorted(results, key=lambda x: x[1], reverse=True)
