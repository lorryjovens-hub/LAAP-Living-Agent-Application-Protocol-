"""LAAP Memory Engine — Muscle Memory (肌肉记忆/程序记忆)
Procedural memory: automated skills and compiled procedures
"""
from __future__ import annotations
import time, json, uuid, logging, hashlib, threading
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("engine.memory.muscle")

class SkillStage(str, Enum):
    COGNITIVE = "cognitive"
    ASSOCIATIVE = "associative"
    AUTONOMOUS = "autonomous"

@dataclass
class CompiledProcedure:
    id: str = field(default_factory=lambda: f"sk_{uuid.uuid4().hex[:10]}")
    name: str = ""
    description: str = ""
    code: str = ""
    signature: str = ""
    avg_execution_time: float = 0.0
    invocation_count: int = 0
    last_invoked: float = field(default_factory=time.time)
    stage: SkillStage = SkillStage.COGNITIVE
    confidence: float = 0.3
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "stage": self.stage.value,
                "invocations": self.invocation_count, "confidence": self.confidence}

class SkillCache:
    def __init__(self, max_size: int = 100):
        self._cache: OrderedDict[str, CompiledProcedure] = OrderedDict()
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[CompiledProcedure]:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None
    
    def put(self, key: str, proc: CompiledProcedure):
        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)
        self._cache[key] = proc
    
    def remove(self, key: str):
        self._cache.pop(key, None)
    
    def clear(self):
        self._cache.clear()
    
    def get_stats(self) -> dict:
        return {"size": len(self._cache), "max_size": self.max_size}

class MuscleMemory:
    def __init__(self):
        self._procedures: Dict[str, CompiledProcedure] = {}
        self._cache = SkillCache()
        self._lock = threading.RLock()
    
    def learn(self, name: str, code: str, description: str = "") -> str:
        sig = hashlib.sha256(code.encode()).hexdigest()[:16]
        with self._lock:
            for pid, proc in self._procedures.items():
                if proc.signature == sig:
                    return pid
            proc = CompiledProcedure(name=name, code=code, signature=sig, description=description)
            self._procedures[proc.id] = proc
            self._cache.put(name, proc)
        return proc.id
    
    def execute(self, proc_id_or_name: str, *args, **kwargs) -> Any:
        proc = self._procedures.get(proc_id_or_name) or self._cache.get(proc_id_or_name)
        if not proc:
            raise KeyError(f"Procedure not found: {proc_id_or_name}")
        start = time.time()
        try:
            compiled = compile(proc.code, f"<muscle_{proc.id}>", "exec")
            namespace = {}
            exec(compiled, namespace)
            result = None
            if "execute" in namespace:
                result = namespace["execute"](*args, **kwargs)
            proc.invocation_count += 1
            proc.last_invoked = time.time()
            elapsed = time.time() - start
            proc.avg_execution_time = (proc.avg_execution_time * (proc.invocation_count - 1) + elapsed) / proc.invocation_count
            if proc.invocation_count > 10:
                proc.stage = SkillStage.ASSOCIATIVE
            if proc.invocation_count > 50:
                proc.stage = SkillStage.AUTONOMOUS
            proc.confidence = min(1.0, proc.confidence + 0.02)
            return result
        except Exception as e:
            logger.error(f"Muscle execution failed: {e}")
            raise
    
    def get_skill(self, name: str) -> Optional[CompiledProcedure]:
        for proc in self._procedures.values():
            if proc.name == name:
                return proc
        return self._cache.get(name)
    
    def list_skills(self, stage: Optional[SkillStage] = None) -> List[CompiledProcedure]:
        if stage:
            return [p for p in self._procedures.values() if p.stage == stage]
        return list(self._procedures.values())
    
    def forget_unused(self, days_threshold: float = 30) -> int:
        cutoff = time.time() - days_threshold * 86400
        to_remove = [pid for pid, p in self._procedures.items() if p.last_invoked < cutoff]
        for pid in to_remove:
            del self._procedures[pid]
        return len(to_remove)
    
    def get_stats(self) -> dict:
        stages = {s.value: 0 for s in SkillStage}
        for p in self._procedures.values():
            stages[p.stage.value] += 1
        return {"total": len(self._procedures), "stages": stages}
