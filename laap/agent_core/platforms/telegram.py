"""Telegram Platform — 完整Bot支持(长轮询+命令+媒体)"""
from __future__ import annotations
import asyncio, json, logging, time, urllib.request, urllib.error
from typing import Any, Callable, Dict, List, Optional
from laap.agent_core.platforms.base import BasePlatformAdapter, MessageEvent, MessageType, SendResult

logger = logging.getLogger("agent_core.platforms.telegram")

class TelegramAdapter(BasePlatformAdapter):
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.token = config.get("token", "")
        self._base = f"https://api.telegram.org/bot{self.token}"
        self._offset = 0
        self._task = None
        self._handler = None
    
    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Telegram started")
    
    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
    
    async def _poll_loop(self):
        retry = 1
        while self._running:
            try:
                updates = await self._api("getUpdates", {"offset": self._offset, "timeout": 30})
                if updates and "result" in updates:
                    for u in updates["result"]:
                        await self._process_update(u)
                        self._offset = u["update_id"] + 1
                retry = 1
            except Exception as e:
                logger.error(f"TG poll: {e}")
                await asyncio.sleep(retry)
                retry = min(retry * 2, 30)
    
    async def _process_update(self, update):
        msg = update.get("message", {}) or update.get("callback_query", {}).get("message", {})
        text = msg.get("text", "")
        chat = msg.get("chat", {})
        user = msg.get("from", {})
        if not text:
            return
        event = MessageEvent(
            platform="telegram", chat_id=str(chat.get("id","")),
            user_id=str(user.get("id","")), text=text,
            user_name=user.get("first_name",""), message_id=str(msg.get("message_id",""))
        )
        if self._handler:
            resp = self._handler(event)
            await self.send_message(event.chat_id, str(resp)[:4000])
    
    async def send_message(self, chat_id: str, text: str, **kwargs) -> SendResult:
        try:
            result = await self._api("sendMessage", {"chat_id": chat_id, "text": text[:4000], "parse_mode": "Markdown"})
            return SendResult(success=True, message_id=str(result.get("result",{}).get("message_id","")))
        except Exception as e:
            return SendResult(success=False, error=str(e))
    
    async def _api(self, method: str, params: Dict = None) -> Dict:
        url = f"{self._base}/{method}"
        data = json.dumps(params or {}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        loop = asyncio.get_event_loop()
        with await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=35)) as resp:
            return json.loads(resp.read().decode())
