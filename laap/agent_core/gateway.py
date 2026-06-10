"""Gateway — 平台网关接入 (Telegram + Discord)"""
from __future__ import annotations
import asyncio, json, logging, os, time, uuid, threading
from typing import Any, Callable, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError

logger = logging.getLogger("agent_core.gateway")

class TelegramBot:
    """Telegram Bot — 长轮询模式"""
    def __init__(self, token: str, agent=None):
        self.token = token
        self.agent = agent
        self._base = f"https://api.telegram.org/bot{token}"
        self._offset = 0
        self._running = False
        self._thread = None
    
    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("Telegram bot started")
    
    def stop(self):
        self._running = False
        logger.info("Telegram bot stopped")
    
    def _poll_loop(self):
        while self._running:
            try:
                data = self._api("getUpdates", {"offset": self._offset, "timeout": 30})
                if data and "result" in data:
                    for update in data["result"]:
                        self._handle_update(update)
                        self._offset = update["update_id"] + 1
            except Exception as e:
                if self._running:
                    logger.error(f"Poll error: {e}")
                    time.sleep(5)
    
    def _handle_update(self, update):
        msg = update.get("message", {})
        text = msg.get("text", "")
        if not text:
            return
        chat_id = msg.get("chat", {}).get("id")
        if not chat_id:
            return
        if text.startswith("/"):
            cmds = {"/start": "🐉 LAAP Gateway ready!", "/help": "Commands: /start, /help, /status"}
            self._api("sendMessage", {"chat_id": chat_id, "text": cmds.get(text.split()[0].lower(), "Unknown command")})
            return
        if self.agent:
            response = self.agent.chat(text)
            self._api("sendMessage", {"chat_id": chat_id, "text": response[:4000]})
    
    def _api(self, method, params=None):
        import urllib.request
        url = f"{self._base}/{method}"
        data = json.dumps(params or {}).encode() if params else None
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=35) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            logger.error(f"TG API {method}: {e}")
            return None

class SimpleGateway:
    """简易网关管理器"""
    def __init__(self, agent=None):
        self.agent = agent
        self._bots = {}
    
    def add_telegram(self, token: str):
        bot = TelegramBot(token, self.agent)
        self._bots["telegram"] = bot
        return bot
    
    def start_all(self):
        for name, bot in self._bots.items():
            bot.start()
            logger.info(f"Gateway {name} started")
    
    def stop_all(self):
        for name, bot in self._bots.items():
            bot.stop()
            logger.info(f"Gateway {name} stopped")
