"""Webhook Platform — 通用Webhook接收"""
from __future__ import annotations
import json, logging, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Callable, Dict, List, Optional
from laap.agent_core.platforms.base import BasePlatformAdapter, MessageEvent, SendResult

logger = logging.getLogger("agent_core.platforms.webhook")

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        if hasattr(self.server, "adapter") and self.server.adapter._handler:
            event = MessageEvent(platform="webhook", text=body[:2000])
            self.server.adapter._handler(event)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')
    def log_message(self, format, *args): pass

class WebhookAdapter(BasePlatformAdapter):
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.port = config.get("port", 8888)
        self._server = None
    
    async def start(self):
        self._running = True
        self._server = HTTPServer(("0.0.0.0", self.port), WebhookHandler)
        self._server.adapter = self
        import threading
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info(f"Webhook listening on :{self.port}")
    
    async def stop(self):
        self._running = False
        if self._server:
            self._server.shutdown()
    
    async def send_message(self, chat_id: str, text: str, **kwargs) -> SendResult:
        return SendResult(success=True, message_id="webhook_async")
