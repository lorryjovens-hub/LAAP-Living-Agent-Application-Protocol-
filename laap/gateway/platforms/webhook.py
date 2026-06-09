"""LAAP Gateway — Webhook API Server

FastAPI-based webhook server for receiving messages from
custom integrations and external services.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Any, Dict, List, Optional

from laap.gateway.base import BaseAdapter

logger = logging.getLogger("laap.gateway.webhook")


class WebhookAdapter(BaseAdapter):
    """Webhook API server adapter using FastAPI."""

    platform_name = "webhook"

    def __init__(self, config: Dict[str, Any], engine):
        super().__init__(config, engine)
        self._host = config.get("host", "127.0.0.1")
        self._port = int(config.get("port", 8765))
        self._api_key = config.get("api_key", "")
        self._server = None

    async def start(self):
        try:
            from fastapi import FastAPI, HTTPException, Header
            import uvicorn
        except ImportError:
            logger.error("Webhook: pip install fastapi uvicorn")
            return

        self._running = True

        app = FastAPI(title="LAAP Gateway", version="0.1.0")

        @app.get("/health")
        async def health():
            return {"status": "ok", "agent": "laap", "version": "0.3.0"}

        @app.post("/webhook")
        async def webhook(data: Dict[str, Any],
                          authorization: str = Header(None)):
            if self._api_key:
                if not authorization or authorization != f"Bearer {self._api_key}":
                    raise HTTPException(status_code=403, detail="Forbidden")

            text = data.get("text", "")
            chat_id = data.get("chat_id", "webhook-default")
            user_id = data.get("user_id", "webhook-user")

            if not text:
                raise HTTPException(status_code=400, detail="No text provided")

            response = await self._process_text(
                chat_id=chat_id, user_id=user_id, text=text,
            )

            return {"response": response}

        logger.info(f"Webhook server starting on {self._host}:{self._port}")
        config = uvicorn.Config(app, host=self._host, port=self._port,
                                log_level="info")
        self._server = uvicorn.Server(config)
        await self._server.serve()

    async def stop(self):
        self._running = False
        if self._server:
            self._server.should_exit = True
        logger.info("Webhook adapter stopped")

    async def send_message(self, chat_id: str, text: str,
                           parse_mode: Optional[str] = None) -> bool:
        return True  # Webhook is receive-only
