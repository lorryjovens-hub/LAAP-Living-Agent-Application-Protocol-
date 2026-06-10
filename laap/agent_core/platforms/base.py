"""BasePlatformAdapter — 完整基类（深度集成）"""
from __future__ import annotations
import time, json, logging, abc, asyncio, hashlib, threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("agent_core.platforms.base")

class MessageType(str, Enum):
    TEXT = "text"; IMAGE = "image"; FILE = "file"; AUDIO = "audio"
    VIDEO = "video"; STICKER = "sticker"; COMMAND = "command"
    CARD = "card"; MARKDOWN = "markdown"; POST = "post"

@dataclass
class MessageEvent:
    platform: str = ""; chat_id: str = ""; user_id: str = ""
    text: str = ""; msg_type: MessageType = MessageType.TEXT
    user_name: str = ""; message_id: str = ""
    raw: Dict = field(default_factory=dict); timestamp: float = field(default_factory=time.time)
    media_url: str = ""; reply_to: str = ""

@dataclass
class SendResult:
    success: bool = True; message_id: str = ""; error: str = ""

class BasePlatformAdapter(abc.ABC):
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self._running = False
        self._handler: Optional[Callable] = None
        self._retry_delay = 1
        self._max_retries = 5
        self._rate_limit = RateLimiter(30, 60)
        self._stats = {"messages_sent": 0, "messages_received": 0,
                       "errors": 0, "reconnects": 0, "start_time": 0.0}
        self._token: str = ""
        self._token_expire: float = 0.0
        self._webhook_secret: str = config.get("webhook_secret", "") if config else ""
    
    @abc.abstractmethod
    async def start(self): ...
    @abc.abstractmethod
    async def stop(self): ...
    @abc.abstractmethod
    async def send_message(self, chat_id: str, text: str, **kwargs) -> SendResult: ...
    
    async def send_text(self, chat_id: str, text: str) -> SendResult:
        return await self.send_message(chat_id, text)
    
    async def send_image(self, chat_id: str, image_url: str) -> SendResult:
        return await self.send_message(chat_id, f"[图片] {image_url}")
    
    async def send_card(self, chat_id: str, title: str, content: str, **kwargs) -> SendResult:
        return await self.send_message(chat_id, f"**{title}**\n{content}")
    
    async def send_typing(self, chat_id: str) -> bool: return True
    
    def set_handler(self, handler: Callable):
        self._handler = handler
    
    async def _safe_call(self, coro, retries=None):
        retries = retries or self._max_retries
        for i in range(retries):
            try:
                return await coro
            except Exception as e:
                self._stats["errors"] += 1
                if i == retries - 1: raise
                await asyncio.sleep(self._retry_delay * (2 ** i))
    
    async def _ensure_token(self):
        if time.time() >= self._token_expire - 60:
            await self._refresh_token()
    
    async def _refresh_token(self):
        pass  # Override for platforms that need tokens
    
    def get_stats(self) -> dict:
        uptime = time.time() - self._stats.get("start_time", time.time())
        return dict(self._stats, uptime=round(uptime, 1), running=self._running)
    
    @property
    def name(self) -> str:
        return self.__class__.__name__.replace("Adapter", "").lower()

class RateLimiter:
    def __init__(self, max_per_minute: int = 30, max_per_second: int = 5):
        self.max_per_minute = max_per_minute
        self.max_per_second = max_per_second
        self._calls: List[float] = []
        self._lock = threading.RLock()
    
    def acquire(self) -> bool:
        now = time.time()
        with self._lock:
            self._calls = [t for t in self._calls if now - t < 60]
            if len(self._calls) >= self.max_per_minute:
                return False
            self._calls.append(now)
            return True
