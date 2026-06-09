"""LAAP Gateway — Discord Adapter

Full Discord bot adapter with slash commands and message streaming.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Any, Dict, List, Optional

from laap.gateway.base import BaseAdapter

logger = logging.getLogger("laap.gateway.discord")


class DiscordAdapter(BaseAdapter):
    """Discord bot adapter."""

    platform_name = "discord"

    def __init__(self, config: Dict[str, Any], engine):
        super().__init__(config, engine)
        self._token = config.get("token", "")
        self._allowed_channels: List[str] = config.get("allowed_channels", [])
        self._client = None

    async def start(self):
        if not self._token:
            logger.error("Discord: no token configured")
            return

        try:
            import discord
            from discord.ext import commands
        except ImportError:
            logger.error("Discord: pip install discord.py")
            return

        self._running = True
        intents = discord.Intents.default()
        intents.message_content = True

        self._client = commands.Bot(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )

        @self._client.event
        async def on_ready():
            logger.info(f"Discord bot ready: {self._client.user}")

        @self._client.event
        async def on_message(message):
            if message.author.bot:
                return
            if self._allowed_channels and str(message.channel.id) not in self._allowed_channels:
                return

            ctx = await self._client.get_context(message)
            if ctx.valid and ctx.command:
                await self._client.invoke(ctx)
                return

            # Process text through engine
            cid = str(message.channel.id)
            uid = str(message.author.id)
            name = message.author.display_name
            text = message.content

            async with message.channel.typing():
                response = await self._process_text(
                    chat_id=cid, user_id=uid, text=text, user_name=name,
                )

            if len(response) > 1900:
                for i in range(0, len(response), 1900):
                    await message.channel.send(response[i:i+1900])
            else:
                await message.channel.send(response)

        @self._client.command(name="start")
        async def cmd_start(ctx):
            await ctx.send("🐉 **LAAP Golden Dragon awake!** Send me a message.")

        @self._client.command(name="help")
        async def cmd_help(ctx):
            await ctx.send("🐉 **Commands:** !start, !help, !new, !status")

        @self._client.command(name="new")
        async def cmd_new(ctx):
            await ctx.send("🔄 Session reset. Dragon ready.")

        @self._client.command(name="status")
        async def cmd_status(ctx):
            from laap import __version__ as ver
            await ctx.send(f"🐉 **LAAP v{ver}** | PSI Cognitive | RSI Evolution")

        # Start the bot
        try:
            await self._client.start(self._token)
        except Exception as e:
            logger.error(f"Discord error: {e}")

    async def stop(self):
        self._running = False
        if self._client:
            try:
                await self._client.close()
            except Exception:
                pass
        logger.info("Discord adapter stopped")

    async def send_message(self, chat_id: str, text: str,
                           parse_mode: Optional[str] = None) -> bool:
        if not self._client:
            return False
        try:
            channel = self._client.get_channel(int(chat_id))
            if channel:
                await channel.send(text)
                return True
            return False
        except Exception as e:
            logger.error(f"Discord send error: {e}")
            return False
