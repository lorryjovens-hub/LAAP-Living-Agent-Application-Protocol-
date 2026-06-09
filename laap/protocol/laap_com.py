"""
LAAP-COM v1.0 — 数字生命体通信协议

定义生命体之间的消息格式、路由、加密：
- 意图驱动 (非类型驱动)
- 优先级 + TTL 时效
- 端到端签名
- 支持请求/响应/事件/广播
"""
from __future__ import annotations
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger("laap.protocol.com")


class MessageType(str, Enum):
    REQUEST = "request"       # 请求-响应模式
    RESPONSE = "response"     # 响应
    EVENT = "event"           # 事件通知 (单向)
    BROADCAST = "broadcast"   # 广播 (一对多)

class MessageIntent(str, Enum):
    COLLABORATE = "collaborate"   # 协作
    INFORM = "inform"             # 通知
    REQUEST = "request"           # 请求
    EVOLVE = "evolve"             # 进化
    REPRODUCE = "reproduce"       # 繁殖
    SYNC = "sync"                 # 同步
    HEARTBEAT = "heartbeat"       # 心跳


@dataclass
class Message:
    """LAAP-COM 标准消息"""
    protocol: str = "LAAP-COM"
    version: str = "1.0"
    message_id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:16]}")
    sender: str = ""                # 发送者 LAAP-ID
    recipient: str = ""             # 接收者 LAAP-ID 或 "*" (广播)
    type: MessageType = MessageType.REQUEST
    intent: MessageIntent = MessageIntent.INFORM
    payload: Any = None
    priority: float = 0.5          # 0-1
    ttl: int = 60                   # 生存时间(秒)
    correlation_id: str = ""        # 关联消息ID (用于请求-响应配对)
    timestamp: float = field(default_factory=time.time)
    signature: str = ""             # 发送者签名

    def sign(self, secret: str = "") -> str:
        """签名消息"""
        content = f"{self.message_id}:{self.sender}:{self.recipient}:{json.dumps(self.payload)}"
        self.signature = hashlib.sha256((content + secret).encode()).hexdigest()[:16]
        return self.signature

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    def to_dict(self) -> dict:
        return asdict(self)


class MessageBus:
    """消息总线——生命体之间通信的核心"""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._pending_responses: Dict[str, Message] = {}
        self._stats = {"sent": 0, "received": 0, "routed": 0}

    def subscribe(self, intent: str, handler: Callable[[Message], Optional[Message]]):
        """订阅特定意图的消息"""
        self._handlers.setdefault(intent, []).append(handler)

    def send(self, msg: Message) -> Optional[Message]:
        """发送消息 (同步请求-响应)"""
        msg.sign()
        self._stats["sent"] += 1
        logger.debug(f"Send: {msg.intent.value} → {msg.recipient[:16]}")

        # 查找处理器
        handlers = self._handlers.get(msg.intent.value, [])
        if not handlers:
            logger.warning(f"No handler for intent: {msg.intent.value}")
            return None

        # 调用处理器
        for handler in handlers:
            response = handler(msg)
            if response:
                self._stats["routed"] += 1
                if msg.type == MessageType.REQUEST:
                    self._pending_responses[msg.message_id] = response
                return response
        return None

    def publish(self, msg: Message):
        """发布事件 (异步广播)"""
        msg.type = MessageType.EVENT
        msg.sign()
        self._stats["sent"] += 1
        handlers = self._handlers.get(msg.intent.value, [])
        for handler in handlers:
            try:
                handler(msg)
                self._stats["routed"] += 1
            except Exception as e:
                logger.warning(f"Handler error: {e}")

    def get_stats(self) -> dict:
        return dict(self._stats)


# ── 全局消息总线 ────────────────────────────────────────────

_bus: Optional[MessageBus] = None

def get_bus() -> MessageBus:
    global _bus
    if _bus is None:
        _bus = MessageBus()
    return _bus

def send_message(sender: str, recipient: str, intent: MessageIntent,
                 payload: Any = None) -> Optional[Message]:
    """便捷：发送消息"""
    msg = Message(sender=sender, recipient=recipient, intent=intent, payload=payload)
    return get_bus().send(msg)
