"""Slack Platform — Bot支持(Socket Mode)"""
from __future__ import annotations
import asyncio, json, logging, time, urllib.request
from typing import Any, Callable, Dict, List, Optional
from laap.agent_core.platforms.base import BasePlatformAdapter, MessageEvent, MessageType, SendResult

logger = logging.getLogger("agent_core.platforms.slack")

class SlackAdapter(BasePlatformAdapter):
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.token = config.get("token", "")
        self._base = "https://slack.com/api"
        self._headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        self._task = None
        self._handler = None
    
    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._health_loop())
        logger.info("Slack started")
    
    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
    
    async def _health_loop(self):
        while self._running:
            await asyncio.sleep(60)
    
    async def send_message(self, channel_id: str, text: str, **kwargs) -> SendResult:
        try:
            url = f"{self._base}/chat.postMessage"
            data = json.dumps({"channel": channel_id, "text": text[:3000]}).encode()
            req = urllib.request.Request(url, data=data, headers=self._headers, method="POST")
            loop = asyncio.get_event_loop()
            with await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=15)) as resp:
                return SendResult(success=True)
        except Exception as e:
            return SendResult(success=False, error=str(e))
