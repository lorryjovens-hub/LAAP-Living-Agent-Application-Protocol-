"""Lifeform Messenger — 生命体间通信"""
from __future__ import annotations
import time, json, uuid, logging, threading
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from laap.protocol.laap_com import Message, MessageType, MessageIntent, MessageBus

logger = logging.getLogger("engine.collaboration.messenger")

class DeliveryGuarantee(str, Enum):
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"

@dataclass
class DeliveryReceipt:
    message_id: str = ""
    delivered: bool = False
    delivered_at: float = field(default_factory=time.time)
    error: str = ""

class LifeformMessenger:
    def __init__(self, identity: str = ""):
        self.identity = identity
        self.bus = MessageBus()
        self._handlers: Dict[str, Callable] = {}
        self._pending: Dict[str, Dict] = {}
        self._lock = threading.RLock()
    def send(self, recipient: str, payload: Any, msg_type: str = "request",
             intent: str = "inform", ttl: int = 60) -> str:
        msg = Message(sender=self.identity, recipient=recipient,
                     type=MessageType(msg_type), intent=MessageIntent(intent),
                     payload=payload, ttl=ttl)
        msg.sign()
        with self._lock:
            self._pending[msg.message_id] = {"msg": msg, "attempts": 0, "max_attempts": 3}
        self.bus.publish(msg)
        logger.info(f"Sent message {msg.message_id} to {recipient}")
        return msg.message_id
    def broadcast(self, recipients: List[str], payload: Any, intent: str = "inform"):
        for r in recipients:
            self.send(r, payload, "broadcast", intent)
    def on_message(self, msg_type: str, handler: Callable):
        self._handlers[msg_type] = handler
    def receive(self, message: Message):
        handler = self._handlers.get(message.type.value) or self._handlers.get("*")
        if handler:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Handler error: {e}")
    def retry_pending(self) -> int:
        retried = 0
        with self._lock:
            for mid, info in list(self._pending.items()):
                if info["attempts"] < info["max_attempts"]:
                    info["attempts"] += 1
                    self.bus.publish(info["msg"])
                    retried += 1
                else:
                    del self._pending[mid]
        return retried
    def get_stats(self) -> dict:
        return {"pending": len(self._pending), "handlers": len(self._handlers)}
