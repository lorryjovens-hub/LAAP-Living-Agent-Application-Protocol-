"""
LAAP — Agent 间通信协议
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class MessageType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    FORK = "fork_request"
    FUSION = "fusion_proposal"
    STATUS = "status_report"
    NULL_INJECT = "null_injection"


@dataclass
class AgentMessage:
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    msg_type: MessageType = MessageType.REQUEST
    sender_id: str = ""
    target_id: str = ""
    content: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {"id": self.msg_id, "type": self.msg_type.value,
                "from": self.sender_id[:8], "to": self.target_id[:8],
                "content": self.content[:60], "priority": self.priority}


class MessageRouter:
    """消息路由器"""

    def __init__(self):
        self.queues: Dict[str, List[AgentMessage]] = {}
        self._sent: List[AgentMessage] = []

    def send(self, msg: AgentMessage):
        self.queues.setdefault(msg.target_id, []).append(msg)
        self._sent.append(msg)

    def broadcast(self, msg: AgentMessage, targets: List[str]):
        for t in targets:
            copy = AgentMessage(msg_type=msg.msg_type, sender_id=msg.sender_id,
                                target_id=t, content=msg.content, payload=msg.payload.copy())
            self.send(copy)

    def receive(self, agent_id: str) -> List[AgentMessage]:
        msgs = self.queues.get(agent_id, [])
        self.queues[agent_id] = []
        return msgs

    def status(self) -> dict:
        return {k: len(v) for k, v in self.queues.items() if v}
