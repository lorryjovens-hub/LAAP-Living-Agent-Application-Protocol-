"""
LAAP — 层次化记忆系统

基于 PSI 理论的记忆层次：
  工作记忆 → 情景记忆 → 语义记忆 → 程序记忆（技能）
  向量记忆（语义检索）

类比人类记忆：工作记忆是"当前在想什么"，
情景记忆是"经历了什么"，语义记忆是"知道了什么"，
程序记忆是"会做什么"。
"""

from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import json, logging, hashlib

logger = logging.getLogger("laap.memory")



@dataclass
class MemoryItem:
    content: str
    tags: List[str] = field(default_factory=list)
    emotional_valence: float = 0.0
    importance: float = 0.5
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    access_count: int = 0
    embedding: Optional[List[float]] = None

    @property
    def age(self) -> float:
        return datetime.now().timestamp() - self.timestamp

    def to_dict(self) -> dict:
        return {
            "content": self.content[:120],
            "tags": self.tags,
            "valence": round(self.emotional_valence, 2),
            "importance": round(self.importance, 2),
            "age_s": round(self.age, 1),
            "access_count": self.access_count,
        }


@dataclass
class Skill:
    name: str
    description: str = ""
    proficiency: float = 0.0
    success_count: int = 0
    fail_count: int = 0
    code: Optional[str] = None

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / total if total > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "proficiency": round(self.proficiency, 2),
            "success_rate": round(self.success_rate, 3),
        }


@dataclass
class Reflection:
    episode: int
    observation: str
    hypothesis: str
    outcome: str = ""
    reward_delta: float = 0.0
    adopted: bool = False
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())

    def to_dict(self) -> dict:
        return {
            "episode": self.episode,
            "observation": self.observation[:60],
            "hypothesis": self.hypothesis[:60],
            "outcome": self.outcome[:60],
            "reward_delta": round(self.reward_delta, 3),
            "adopted": self.adopted,
        }


class HierarchicalMemory:
    """层次化记忆系统 (支持 Rust + QLAM 量子后端)"""

    def __init__(self, wm_size: int = 9, use_rust: bool = True,
                 use_quantum: bool = False, n_qubits: int = 4):
        self.wm: deque = deque(maxlen=wm_size)
        self.episodic: List[MemoryItem] = []
        self.semantic: Dict[str, MemoryItem] = {}
        self.skills: Dict[str, Skill] = {}
        self.reflections: List[Reflection] = []
        self.total_items = 0
        self.forgotten = 0
        self._rust = None  # Lazy Rust backend
        self._quantum = None  # Lazy QLAM backend
        if use_rust:
            try:
                from laap.memory.rust_backend import rust_available, RustMemoryEngine, RustTokenCounter
                if rust_available():
                    self._rust = {
                        "engine": RustMemoryEngine(),
                        "token_counter": RustTokenCounter(),
                    }
                    logger.info("Rust memory backend active")
            except Exception:
                pass
        if use_quantum:
            try:
                from laap.memory.quantum import QLAMMemory
                self._quantum = QLAMMemory(n_qubits=n_qubits)
                logger.info(f"QLAM quantum memory active ({n_qubits} qubits)")
            except Exception as e:
                logger.warning(f"QLAM init failed (quantum sim missing): {e}")

    def perceive(self, content: str, tags=None, valence=0.0, importance=0.5):
        self.wm.append(MemoryItem(content=content, tags=tags or [],
                                  emotional_valence=valence, importance=importance))

    def remember(self, content: str, tags=None, valence=0.0, importance=0.5):
        self.episodic.append(MemoryItem(content=content, tags=tags or [],
                                        emotional_valence=valence, importance=importance))
        self.total_items += 1

    def recall(self, query_tags=None, limit=10, min_importance=0.0) -> List[MemoryItem]:
        results = []
        for item in reversed(self.episodic):
            if item.importance < min_importance:
                continue
            if query_tags and not any(t in item.tags for t in query_tags):
                continue
            results.append(item)
            item.access_count += 1
            if len(results) >= limit:
                break
        return results

    def learn(self, key: str, content: str, importance=0.5):
        if key in self.semantic:
            existing = self.semantic[key]
            existing.content = content
            existing.importance = max(existing.importance, importance)
            existing.access_count += 1
        else:
            self.semantic[key] = MemoryItem(content=content, tags=["semantic"],
                                            importance=importance)
            self.total_items += 1

    def know(self, key: str) -> Optional[str]:
        item = self.semantic.get(key)
        if item:
            item.access_count += 1
            return item.content
        return None

    def register_skill(self, name: str, description="", code=None):
        if name not in self.skills:
            self.skills[name] = Skill(name=name, description=description, code=code)

    def record_skill_result(self, name: str, success: bool, delta=0.01):
        skill = self.skills.get(name)
        if not skill:
            return
        if success:
            skill.success_count += 1
        else:
            skill.fail_count += 1
        skill.proficiency = max(0.0, min(1.0, skill.proficiency + (delta if success else -delta)))

    def best_skills(self, n=3) -> List[Skill]:
        return sorted(self.skills.values(), key=lambda s: s.proficiency, reverse=True)[:n]

    def add_reflection(self, ref: Reflection):
        self.reflections.append(ref)

    def recent_reflections(self, n=5) -> List[Reflection]:
        return self.reflections[-n:]

    def forget(self, max_age=3600.0, max_episodic=1000):
        before = len(self.episodic)
        self.episodic = [m for m in self.episodic
                         if m.age < max_age or m.importance > 0.7]
        if len(self.episodic) > max_episodic:
            self.episodic = self.episodic[-max_episodic:]
        self.forgotten += before - len(self.episodic)

    def to_dict(self) -> dict:
        return {
            "wm": len(self.wm), "episodic": len(self.episodic),
            "semantic": len(self.semantic), "skills": len(self.skills),
            "reflections": len(self.reflections), "forgotten": self.forgotten,
            "top_skills": [s.to_dict() for s in self.best_skills(3)],
        }

    # ── Persistent Storage ──

    def _memory_path(self) -> Path:
        from pathlib import Path as _P
        p = _P.home() / ".laap" / "memory"
        p.mkdir(parents=True, exist_ok=True)
        return p / "hierarchical.json"

    def save(self) -> bool:
        """Persist hierarchical memory to disk as JSON."""
        import json, datetime as _dt
        try:
            data = {
                "episodic": [{"content": m.content, "tags": m.tags,
                              "emotional_valence": m.emotional_valence,
                              "importance": m.importance,
                              "timestamp": m.timestamp,
                              "access_count": m.access_count} for m in self.episodic],
                "semantic": {k: {"content": v.content, "tags": v.tags,
                                 "importance": v.importance,
                                 "timestamp": v.timestamp,
                                 "access_count": v.access_count}
                             for k, v in self.semantic.items()},
                "skills": {k: {"description": v.description,
                               "proficiency": v.proficiency,
                               "success_count": v.success_count,
                               "fail_count": v.fail_count, "code": v.code}
                           for k, v in self.skills.items()},
                "reflections": [{"episode": r.episode, "observation": r.observation,
                                 "hypothesis": r.hypothesis, "outcome": r.outcome,
                                 "reward_delta": r.reward_delta, "adopted": r.adopted,
                                 "timestamp": r.timestamp} for r in self.reflections],
                "total_items": self.total_items,
                "forgotten": self.forgotten,
                "saved_at": _dt.datetime.now().isoformat(),
            }
            self._memory_path().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            return True
        except Exception as e:
            logger.warning(f"Memory save failed: {e}")
            return False

    def load(self) -> bool:
        """Restore hierarchical memory from disk."""
        import json
        p = self._memory_path()
        if not p.exists():
            return False
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            self.episodic = [MemoryItem(**m) for m in data.get("episodic", [])]
            self.semantic = {}
            for k, v in data.get("semantic", {}).items():
                self.semantic[k] = MemoryItem(content=v["content"], tags=v.get("tags", []),
                                              importance=v.get("importance", 0.5),
                                              timestamp=v.get("timestamp", 0.0),
                                              access_count=v.get("access_count", 0))
            self.skills = {}
            for k, v in data.get("skills", {}).items():
                s = Skill(name=k, description=v.get("description", ""),
                          proficiency=v.get("proficiency", 0.0),
                          success_count=v.get("success_count", 0),
                          fail_count=v.get("fail_count", 0), code=v.get("code"))
                self.skills[k] = s
            self.reflections = [Reflection(**r) for r in data.get("reflections", [])]
            self.total_items = data.get("total_items", 0)
            self.forgotten = data.get("forgotten", 0)
            logger.info(f"Memory loaded: {len(self.episodic)} episodic, {len(self.semantic)} semantic, "
                        f"{len(self.skills)} skills, {len(self.reflections)} reflections")
            return True
        except Exception as e:
            logger.warning(f"Memory load failed: {e}")
            return False

    # ── Embedding / Semantic Search ──

    _embedder = None

    def _get_embedder(self):
        """Lazy-initialize the embedding model. Returns a callable or None."""
        if self._embedder is not None:
            return self._embedder

        # Try fastembed first (Rust-based, fastest)
        try:
            from fastembed import TextEmbedding
            model = TextEmbedding()
            self._embedder = lambda texts: list(model.embed(texts))
            logger.info("Embedding: using fastembed (Rust)")
            return self._embedder
        except ImportError:
            pass

        # Try sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2").encode
            logger.info("Embedding: using sentence-transformers")
            return self._embedder
        except ImportError:
            pass

        # Fallback: hash-based pseudo-embedding for compatibility
        logger.info("Embedding: no model found, using hash fallback")
        self._embedder = lambda texts: [
            [float(hashlib.md5(t.encode()).hexdigest()[i:i+2], 16) / 255.0
             for i in range(0, 32, 2)]
            for t in (texts if isinstance(texts, list) else [texts])
        ]
        return self._embedder

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding vector for text."""
        try:
            embedder = self._get_embedder()
            if embedder is None:
                return None
            result = embedder([text])
            if result is not None and len(result) > 0:
                emb = result[0]
                return emb.tolist() if hasattr(emb, 'tolist') else list(emb)
            return None
        except Exception as e:
            logger.debug(f"Embedding failed: {e}")
            return None

    def remember(self, content: str, tags=None, valence=0.0, importance=0.5):
        item = MemoryItem(content=content, tags=tags or [],
                          emotional_valence=valence, importance=importance)
        # Generate embedding
        if importance >= 0.3:
            item.embedding = self._generate_embedding(content)
        self.episodic.append(item)
        self.total_items += 1
        # Rust mirror
        if self._rust:
            try:
                import uuid
                self._rust["engine"].store(str(uuid.uuid4())[:8], content,
                                            "episodic", importance, tags or [], "python")
            except Exception:
                pass
        # QLAM quantum mirror
        if self._quantum:
            try:
                self._quantum.update_from_text(content)
            except Exception:
                pass

    def semantic_search(self, query: str, limit: int = 5) -> List[Tuple[MemoryItem, float]]:
        """Search memories by semantic similarity to query.

        Returns list of (MemoryItem, similarity_score) tuples.
        """
        query_emb = self._generate_embedding(query)
        if query_emb is None:
            return []

        results = []
        for item in self.episodic:
            if item.embedding is None:
                continue
            # Cosine similarity
            a = np.array(query_emb)
            b = np.array(item.embedding)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                continue
            sim = float(np.dot(a, b) / (norm_a * norm_b))
            results.append((item, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def recall(self, query_tags=None, limit=10, min_importance=0.0,
               use_semantic=False, query=None) -> List[MemoryItem]:
        # Try Rust backend first for large memory
        if self._rust and len(self.episodic) > 100 and query:
            try:
                rust_results = self._rust["engine"].recall(
                    query, memory_type=None,
                    tags=query_tags, limit=limit,
                )
                if rust_results:
                    return [MemoryItem(content=r) for r in rust_results]
            except Exception:
                pass

        results = []
        for item in reversed(self.episodic):
            if item.importance < min_importance:
                continue
            if query_tags and not any(t in item.tags for t in query_tags):
                continue
            results.append(item)
            item.access_count += 1
            if len(results) >= limit:
                break

        # Boost results with semantic similarity
        if use_semantic and query:
            semantic = self.semantic_search(query, limit=limit * 2)
            semantic_map = {id(item): score for item, score in semantic}
            # Add semantic boost and re-sort
            for item in results:
                sim = semantic_map.get(id(item), 0)
                if sim > 0.5:
                    item.importance = max(item.importance, sim * 0.3)
            # Re-sort by boost
            results.sort(key=lambda x: semantic_map.get(id(x), 0), reverse=True)

        # QLAM quantum boost (if quantum layer active)
        if self._quantum and query and use_semantic:
            try:
                qemb = np.array(self._generate_embedding(query) or [])
                if len(qemb) > 0:
                    quantum_results = self._quantum.retrieve(qemb, k=limit)
                    q_indices = {idx for idx, _ in quantum_results}
                    # Boost items that match quantum retrieval
                    for idx in q_indices:
                        if idx < len(results):
                            results[idx].importance = min(1.0, results[idx].importance * 1.1)
            except Exception:
                pass

        return results

    def quantum_recall(self, query: str, k: int = 5) -> List[dict]:
        """基于 QLAM 量子态的检索"""
        if not self._quantum:
            return []
        qemb = np.array(self._generate_embedding(query) or [])
        if len(qemb) == 0:
            return []
        results = self._quantum.retrieve(qemb, k=k)
        return [{"state_index": idx, "similarity": round(sim, 4)}
                for idx, sim in results]
