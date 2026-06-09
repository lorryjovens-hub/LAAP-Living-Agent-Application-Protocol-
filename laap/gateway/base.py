"""LAAP Gateway — Base Platform Adapter

Abstract base class for all platform adapters.
Each platform (Telegram, Discord, Slack, etc.) extends this.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from laap.gateway.events import GatewayEvent
from laap.gateway.engine import GatewayEngine

logger = logging.getLogger("laap.gateway.base")


class BaseAdapter:
    """Base class for all platform adapters.

    Subclasses must implement:
        - start() - connect to the platform and begin polling/listening
        - stop() - disconnect gracefully
        - send_message(chat_id, text) - send a text message
    """

    platform_name = "base"

    def __init__(self, config: Dict[str, Any], engine: GatewayEngine):
        self.config = config
        self.engine = engine
        self._running = False
        self._handler: Optional[Callable] = None

    async def start(self):
        """Connect to the platform and start processing messages."""
        self._running = True
        logger.info(f"{self.platform_name} adapter started")

    async def stop(self):
        """Disconnect from the platform."""
        self._running = False
        logger.info(f"{self.platform_name} adapter stopped")

    async def send_message(self, chat_id: str, text: str,
                           parse_mode: Optional[str] = None) -> bool:
        """Send a text message to a chat.

        Args:
            chat_id: Platform-specific chat identifier
            text: Message text to send
            parse_mode: Optional parse mode (e.g., "markdown", "html")

        Returns:
            True if sent successfully
        """
        raise NotImplementedError

    async def send_typing(self, chat_id: str) -> bool:
        """Send typing indicator.

        Args:
            chat_id: Platform-specific chat identifier

        Returns:
            True if sent successfully
        """
        return False

    async def send_image(self, chat_id: str, image_url: str,
                         caption: Optional[str] = None) -> bool:
        """Send an image to a chat."""
        return False

    async def handle_event(self, event: GatewayEvent) -> Optional[str]:
        """Process an incoming event and return the response.

        Override this for platform-specific preprocessing.
        """
        return await self.engine.process_message(
            platform=self.platform_name,
            chat_id=event.chat_id,
            user_id=event.user_id,
            text=event.data if isinstance(event.data, str) else "",
        )

    async def _process_text(self, chat_id: str, user_id: str,
                             text: str, user_name: str = "",
                             chat_name: str = "") -> str:
        """Process text through the engine with typing indicator."""
        # Show typing
        asyncio.create_task(self._keep_typing(chat_id))

        # Process
        response = await self.engine.process_message(
            platform=self.platform_name,
            chat_id=chat_id,
            user_id=user_id,
            text=text,
            user_name=user_name,
            chat_name=chat_name,
        )

        return response

    async def _keep_typing(self, chat_id: str, interval: float = 3.0):
        """Keep sending typing indicator while processing."""
        while self._running:
            try:
                await self.send_typing(chat_id)
                await asyncio.sleep(interval)
            except Exception:
                break
