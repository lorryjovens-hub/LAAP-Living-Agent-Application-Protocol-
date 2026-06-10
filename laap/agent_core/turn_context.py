"""TurnContext — 轮次上下文追踪与管理"""
from __future__ import annotations
import time, json, logging, random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent_core.turn_context")

class TurnStatus(str, Enum):
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ToolCallRecord:
    tool_name: str = ""
    arguments: Dict = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    result: Any = None
    error: str = ""
    retries: int = 0
    status: str = "pending"

class TurnContext:
    """轮次上下文 — 追踪单次对话的完整生命周期"""
    
    def __init__(self):
        self.turn_id: int = 0
        self.user_message: str = ""
        self.assistant_response: str = ""
        self.state: TurnStatus = TurnStatus.STARTED
        self.tool_calls: List[ToolCallRecord] = []
        self.error: str = ""
        self.retry_count: int = 0
        self.start_time: float = 0.0
        self.end_time: Optional[float] = None
        self.tokens_used: int = 0
        self.metadata: Dict = field(default_factory=dict)
    
    def start_turn(self, user_message: str, turn_id: int = 0):
        self.turn_id = turn_id
        self.user_message = user_message
        self.state = TurnStatus.IN_PROGRESS
        self.start_time = time.time()
    
    def record_tool_call(self, tool_name: str, arguments: Dict = None) -> int:
        record = ToolCallRecord(tool_name=tool_name, arguments=arguments or {})
        self.tool_calls.append(record)
        return len(self.tool_calls) - 1
    
    def complete_tool_call(self, index: int, result: Any = None, error: str = ""):
        if 0 <= index < len(self.tool_calls):
            self.tool_calls[index].end_time = time.time()
            self.tool_calls[index].result = result
            self.tool_calls[index].error = error
            self.tool_calls[index].status = "failed" if error else "completed"
    
    def complete_turn(self, response: str = ""):
        self.assistant_response = response
        self.state = TurnStatus.COMPLETED
        self.end_time = time.time()
    
    def fail_turn(self, error: str):
        self.error = error
        self.state = TurnStatus.FAILED
        self.end_time = time.time()
    
    def should_retry(self, max_retries: int = 3) -> bool:
        return self.state == TurnStatus.FAILED and self.retry_count < max_retries
    
    def get_duration_ms(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0
    
    def to_dict(self) -> dict:
        return {"turn_id": self.turn_id, "state": self.state.value,
                "tools": len(self.tool_calls), "tokens": self.tokens_used,
                "duration_ms": self.get_duration_ms(), "error": self.error[:50] if self.error else ""}
