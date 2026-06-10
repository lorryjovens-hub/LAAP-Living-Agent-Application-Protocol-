"""PlatformManager — 管理所有平台（深度集成版）"""
from __future__ import annotations
import asyncio, json, logging, os
from typing import Any, Callable, Dict, List, Optional
from laap.agent_core.platforms.base import BasePlatformAdapter, MessageEvent
from laap.agent_core.platforms.telegram import TelegramAdapter
from laap.agent_core.platforms.discord import DiscordAdapter
from laap.agent_core.platforms.slack import SlackAdapter
from laap.agent_core.platforms.feishu import FeishuAdapter
from laap.agent_core.platforms.wechat import WeChatAdapter
from laap.agent_core.platforms.wecom import WeComAdapter
from laap.agent_core.platforms.dingtalk import DingTalkAdapter
from laap.agent_core.platforms.webhook import WebhookAdapter
from laap.agent_core.platforms.whatsapp import WhatsAppAdapter
from laap.agent_core.platforms.email import EmailAdapter

logger = logging.getLogger("agent_core.platforms.manager")

ALL_PLATFORMS = {
    "telegram": TelegramAdapter, "discord": DiscordAdapter, "slack": SlackAdapter,
    "feishu": FeishuAdapter, "wechat": WeChatAdapter, "wecom": WeComAdapter,
    "dingtalk": DingTalkAdapter, "webhook": WebhookAdapter,
    "whatsapp": WhatsAppAdapter, "email": EmailAdapter,
}

PLATFORM_DETAILS = {
    "telegram": {"name":"Telegram","region":"global","auth":"token"},
    "discord": {"name":"Discord","region":"global","auth":"token"},
    "slack": {"name":"Slack","region":"global","auth":"token"},
    "feishu": {"name":"飞书","region":"china","auth":"app_id+secret"},
    "wechat": {"name":"微信","region":"china","auth":"app_id+secret"},
    "wecom": {"name":"企业微信","region":"china","auth":"corp_id+secret"},
    "dingtalk": {"name":"钉钉","region":"china","auth":"app_key+secret"},
    "webhook": {"name":"Webhook","region":"global","auth":"optional"},
    "whatsapp": {"name":"WhatsApp","region":"global","auth":"token"},
    "email": {"name":"Email","region":"global","auth":"password"},
}

class PlatformManager:
    def __init__(self, handler: Callable = None):
        self._adapters: Dict[str, BasePlatformAdapter] = {}
        self._handler = handler
        self._config_path = os.path.expanduser("~/.laap/gateway.json")
    
    def register(self, name: str, adapter: BasePlatformAdapter):
        self._adapters[name] = adapter
        adapter._handler = self._on_message
    
    def _on_message(self, event: MessageEvent) -> str:
        if self._handler: return self._handler(event)
        return f"[{event.platform}] Echo: {event.text[:50]}"
    
    def configure(self, config: Dict):
        for name, cls in ALL_PLATFORMS.items():
            cfg = config.get(name, {})
            if cfg.get("enabled", False):
                required = {"token","app_id","corp_id","app_key","webhook"}
                has_auth = any(k in cfg for k in required)
                if has_auth:
                    self.register(name, cls(cfg))
                    logger.info(f"Configured: {name}")
    
    def load_config(self):
        cfg = {}
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r') as f:
                    cfg = json.load(f)
            except: pass
        self.configure(cfg)
    
    def list_platforms(self) -> List[str]:
        return list(self._adapters.keys())
    
    def get(self, name: str) -> Optional[BasePlatformAdapter]:
        return self._adapters.get(name)
    
    async def start_all(self):
        for name, adapter in self._adapters.items():
            try: await adapter.start()
            except Exception as e: logger.error(f"Start {name} failed: {e}")
    
    async def stop_all(self):
        for name, adapter in self._adapters.items():
            try: await adapter.stop()
            except Exception as e: logger.error(f"Stop {name} failed: {e}")
    
    def get_stats(self) -> dict:
        total = {"platforms": len(self._adapters), "list": self.list_platforms()}
        for name, adapter in self._adapters.items():
            total[name] = adapter.get_stats()
        return total
