"""LAAP Gateway — Slack Adapter

Full Slack bot adapter with Socket Mode and Events API support.
"""

from __future__ import annotations
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from laap.gateway.base import BaseAdapter

logger = logging.getLogger("laap.gateway.slack")


class SlackAdapter(BaseAdapter):
    """Slack bot adapter supporting Socket Mode."""

    platform_name = "slack"

    def __init__(self, config: Dict[str, Any], engine):
        super().__init__(config, engine)
        self._token = config.get("token", "")
        self._app_token = config.get("app_token", "")
        self._client = None

    async def start(self):
        if not self._token:
            logger.error("Slack: no token configured")
            return

        try:
            from slack_bolt import App
            from slack_bolt.adapter.socket_mode import SocketModeHandler
        except ImportError:
            logger.error("Slack: pip install slack-bolt slack-sdk")
            return

        self._running = True

        self._app = App(token=self._token)

        @self._app.message("")
        async def handle_message(message, say, client):
            text = message.get("text", "")
            user = message.get("user", "")
            channel = message.get("channel", "")

            if not text or message.get("bot_id"):
                return

            response = await self._process_text(
                chat_id=channel, user_id=user, text=text,
            )
            await say(response)

        # Start Socket Mode handler
        try:
            handler = SocketModeHandler(self._app, self._app_token or self._token)
            self._handler = handler
            logger.info("Slack adapter started")
            # Run in background thread to not block
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, handler.start)
        except Exception as e:
            logger.error(f"Slack error: {e}")

    async def stop(self):
        self._running = False
        if self._handler:
            try:
                self._handler.close()
            except Exception:
                pass
        logger.info("Slack adapter stopped")

    async def send_message(self, chat_id: str, text: str,
                           parse_mode: Optional[str] = None) -> bool:
        if not self._app:
            return False
        try:
            self._app.client.chat_postMessage(channel=chat_id, text=text)
            return True
        except Exception as e:
            logger.error(f"Slack send error: {e}")
            return False
