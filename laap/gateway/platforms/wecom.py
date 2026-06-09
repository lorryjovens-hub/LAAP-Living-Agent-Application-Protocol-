"""LAAP Gateway — Enterprise WeChat (企业微信) Adapter"""
from __future__ import annotations
import logging
from typing import Any, Dict, Optional
from laap.gateway.base import BaseAdapter

logger = logging.getLogger("laap.gateway.wecom")


class WeComAdapter(BaseAdapter):
    """企业微信机器人适配器"""
    platform_name = "wecom"

    def __init__(self, config: Dict[str, Any], engine):
        super().__init__(config, engine)
        self._webhook_url = config.get("webhook_url", "")
        self._corp_id = config.get("corp_id", "")
        self._corp_secret = config.get("corp_secret", "")
        self._agent_id = config.get("agent_id", "")

    async def start(self):
        try:
            import httpx
        except ImportError:
            logger.error("WeCom: pip install httpx")
            return
        self._running = True
        logger.info("WeCom adapter ready (requires webhook callback URL)")

    async def stop(self):
        self._running = False

    async def send_message(self, chat_id: str, text: str,
                           parse_mode: Optional[str] = None) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self._webhook_url,
                    json={"msgtype": "text", "text": {"content": text}},
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"WeCom send error: {e}")
            return False
