"""SkillRegistry — 技能注册表"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("skills.registry")

@dataclass
class SkillEntry:
    name: str = ""
    module: Any = None
    enabled: bool = True
    category: str = "general"
    version: str = "1.0"

class SkillRegistry:
    def __init__(self):
        self._entries: Dict[str, SkillEntry] = {}
    
    def register(self, name: str, module: Any, category: str = "general", version: str = "1.0"):
        self._entries[name] = SkillEntry(name=name, module=module, category=category, version=version)
    
    def unregister(self, name: str):
        self._entries.pop(name, None)
    
    def get(self, name: str) -> Optional[SkillEntry]:
        return self._entries.get(name)
    
    def list(self, category: str = "") -> List[SkillEntry]:
        if category:
            return [e for e in self._entries.values() if e.category == category]
        return list(self._entries.values())
    
    def enable(self, name: str):
        if name in self._entries:
            self._entries[name].enabled = True
    
    def disable(self, name: str):
        if name in self._entries:
            self._entries[name].enabled = False
    
    def get_stats(self) -> dict:
        return {"total": len(self._entries), "enabled": sum(1 for e in self._entries.values() if e.enabled)}
