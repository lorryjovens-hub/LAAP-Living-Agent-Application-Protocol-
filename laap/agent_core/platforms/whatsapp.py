"""WhatsApp Platform — WhatsApp Cloud API"""
from __future__ import annotations
import json, logging
from typing import Any, Callable, Dict, List, Optional
from laap.agent_core.platforms.base import BasePlatformAdapter, MessageEvent, SendResult

logger = logging.getLogger("agent_core.platforms.whatsapp")

class WhatsAppAdapter(BasePlatformAdapter):
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.token = config.get("token", "")
        self.phone_id = config.get("phone_id", "")
    
    async def start(self):
        self._running = True
        logger.info("WhatsApp started")
    
    async def stop(self):
        self._running = False
    
    async def send_message(self, chat_id: str, text: str, **kwargs) -> SendResult:
        try:
            import urllib.request
            url = f"https://graph.facebook.com/v18.0/{self.phone_id}/messages"
            data = json.dumps({"messaging_product": "whatsapp", "to": chat_id,
                              "type": "text", "text": {"body": text[:4000]}}).encode()
            headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                return SendResult(success=True)
        except Exception as e:
            return SendResult(success=False, error=str(e))
