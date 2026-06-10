"""
LAAP Agent Context — 智能体上下文管理
管理对话窗口、消息历史、Token计数
"""
from __future__ import annotations
import time, json, logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("agent_core.context")

class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

@dataclass
class Message:
    role: Role = Role.USER
    content: str = ""
    tool_calls: List[Dict] = field(default_factory=list)
    tool_call_id: str = ""
    name: str = ""
    timestamp: float = field(default_factory=time.time)
    token_count: int = 0
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {"role": self.role.value, "content": self.content,
                "tool_calls": self.tool_calls, "tool_call_id": self.tool_call_id,
                "name": self.name, "timestamp": self.timestamp}

class Context:
    """上下文窗口管理 — 滑动窗口 + Token预算控制"""
    
    def __init__(self, max_tokens: int = 128000, max_messages: int = 200):
        self.max_tokens = max_tokens
        self.max_messages = max_messages
        self.messages: List[Message] = []
        self.system_prompt: str = ""
        self._token_counts: List[int] = []
    
    def set_system(self, prompt: str):
        self.system_prompt = prompt
    
    def add(self, role: Role, content: str, tool_calls: List = None,
            tool_call_id: str = "", name: str = ""):
        msg = Message(role=role, content=content, tool_calls=tool_calls or [],
                     tool_call_id=tool_call_id, name=name)
        msg.token_count = self._estimate_tokens(content) + 10
        self.messages.append(msg)
        self._token_counts.append(msg.token_count)
        self._trim()
    
    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 2 + len(text.split())
    
    def _trim(self):
        while len(self.messages) > self.max_messages:
            removed = self.messages.pop(1) if len(self.messages) > 2 else self.messages.pop(0)
            if self._token_counts:
                self._token_counts.pop(0)
        total = sum(self._token_counts)
        while total > self.max_tokens and len(self.messages) > 2:
            removed = self.messages.pop(1)
            if self._token_counts:
                t = self._token_counts.pop(0)
                total -= t
    
    def get_messages(self, include_system: bool = True) -> List[dict]:
        result = []
        if include_system and self.system_prompt:
            result.append({"role": "system", "content": self.system_prompt})
        for msg in self.messages:
            if msg.role == Role.TOOL:
                result.append({"role": "tool", "content": msg.content,
                              "tool_call_id": msg.tool_call_id, "name": msg.name})
            elif msg.tool_calls:
                result.append({"role": "assistant", "content": msg.content or None,
                              "tool_calls": msg.tool_calls})
            elif msg.role == Role.ASSISTANT:
                result.append({"role": "assistant", "content": msg.content})
            elif msg.role == Role.USER:
                result.append({"role": "user", "content": msg.content})
            elif msg.role == Role.SYSTEM:
                result.append({"role": "system", "content": msg.content})
        return result
    
    def total_tokens(self) -> int:
        return sum(self._token_counts) + (self._estimate_tokens(self.system_prompt) if self.system_prompt else 0)
    
    def last_message(self) -> Optional[Message]:
        return self.messages[-1] if self.messages else None
    
    def clear(self):
        self.messages.clear()
        self._token_counts.clear()
    
    def to_dict(self) -> dict:
        return {"system_prompt": self.system_prompt[:100] if self.system_prompt else "",
                "messages": len(self.messages), "total_tokens": self.total_tokens()}
