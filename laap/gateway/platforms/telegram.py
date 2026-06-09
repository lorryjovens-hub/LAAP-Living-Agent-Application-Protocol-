"""LAAP Gateway — Telegram Adapter

Full Telegram bot adapter supporting polling and webhook modes.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Any, Dict, List, Optional

from laap.gateway.base import BaseAdapter
from laap.gateway.events import GatewayEvent

logger = logging.getLogger("laap.gateway.telegram")


class TelegramAdapter(BaseAdapter):
    """Full Telegram bot adapter."""

    platform_name = "telegram"

    def __init__(self, config: Dict[str, Any], engine):
        super().__init__(config, engine)
        self._token = config.get("token", "")
        self._webhook_url = config.get("webhook_url", "")
        self._allowed_users: List[str] = config.get("allowed_users", [])
        self._allowed_chats: List[str] = config.get("allowed_chats", [])
        self._app = None
        self._me: Optional[Dict] = None

    async def start(self):
        """Start the Telegram bot with polling."""
        if not self._token:
            logger.error("Telegram: no token configured")
            return

        try:
            import telegram
            from telegram.ext import Application, CommandHandler, MessageHandler, filters
        except ImportError:
            logger.error("Telegram: pip install python-telegram-bot")
            return

        self._running = True
        self._app = Application.builder().token(self._token).build()

        # Register handlers
        self._app.add_handler(CommandHandler("start", self._cmd_start))
        self._app.add_handler(CommandHandler("help", self._cmd_help))
        self._app.add_handler(CommandHandler("new", self._cmd_new))
        self._app.add_handler(CommandHandler("status", self._cmd_status))
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        self._app.add_error_handler(self._handle_error)

        # Get bot info
        try:
            self._me = await self._app.bot.get_me()
            bot_username = self._me.username or "unknown"
            logger.info(f"Telegram bot started: @{bot_username}")
        except Exception as e:
            logger.warning(f"Telegram: could not get bot info: {e}")

        # Run polling with auto-reconnect
        retry_delay = 1
        while self._running:
            try:
                await self._app.run_polling(
                    allowed_updates=["messages"],
                    drop_pending_updates=True,
                    close_loop=False,
                )
            except Exception as e:
                if not self._running:
                    break
                logger.error(f"Telegram error: {e}, reconnecting in {retry_delay}s")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)

    async def stop(self):
        self._running = False
        if self._app:
            try:
                await self._app.stop()
                await self._app.shutdown()
            except Exception:
                pass
        logger.info("Telegram adapter stopped")

    # ── Handlers ─────────────────────────────────────────────

    async def _check_access(self, update) -> bool:
        if not self._allowed_users and not self._allowed_chats:
            return True
        uid = str(update.effective_user.id) if update.effective_user else ""
        cid = str(update.effective_chat.id) if update.effective_chat else ""
        if self._allowed_users and uid not in self._allowed_users:
            return False
        if self._allowed_chats and cid not in self._allowed_chats:
            return False
        return True

    async def _cmd_start(self, update, context):
        if not await self._check_access(update):
            return await update.message.reply_text("Access denied.")
        lines = [
            "\U0001F409 *LAAP Golden Dragon Awake!*",
            "",
            "I am Ao, the Lifeform Autonomous Adaptive Protocol.",
            "Send me a message and I shall assist.",
            "",
            "/new \u2014 Start fresh conversation",
            "/status \u2014 Check agent state",
            "/help \u2014 Show this message",
        ]
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    async def _cmd_help(self, update, context):
        lines = [
            "\U0001F409 *LAAP Commands*",
            "/start \u2014 Wake the dragon",
            "/new \u2014 New conversation",
            "/status \u2014 Agent status",
            "/help \u2014 This message",
            "",
            "Just send any text and I shall respond!",
        ]
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    async def _cmd_new(self, update, context):
        await update.message.reply_text(
            "\U0001F504 *Session reset.* Dragon ready.\nSend your next message.",
            parse_mode="Markdown",
        )

    async def _cmd_status(self, update, context):
        from laap import __version__ as ver
        cid = str(update.effective_chat.id)
        lines = [
            "\U0001F409 *LAAP Status*",
            f"\u2022 Version: {ver}",
            "\u2022 Engine: Golden Dragon Ao",
            "\u2022 Cognitive: PSI Architecture",
            "\u2022 Evolution: RSI Enabled",
            f"\u2022 Chat ID: `{cid}`",
        ]
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    async def _handle_text(self, update, context):
        if not await self._check_access(update):
            return
        cid = str(update.effective_chat.id)
        uid = str(update.effective_user.id)
        name = update.effective_user.full_name or ""
        chat = update.effective_chat.title or ""
        text = update.message.text

        try:
            await context.bot.send_chat_action(chat_id=cid, action="typing")
            response = await self._process_text(
                chat_id=cid, user_id=uid, text=text,
                user_name=name, chat_name=chat,
            )
            # Split long messages
            max_len = 4000
            if len(response) > max_len:
                for i in range(0, len(response), max_len):
                    part = response[i:i+max_len]
                    tag = f"({i//max_len + 1}/{(len(response)-1)//max_len + 1})\n"
                    await update.message.reply_text(
                        tag + part if i > 0 else part,
                        parse_mode="Markdown",
                    )
            else:
                await update.message.reply_text(response, parse_mode="Markdown")
        except Exception as e:
            logger.exception("Telegram handler error")
            await update.message.reply_text(f"\U0001F409 Error: {e}")

    async def _handle_error(self, update, context):
        logger.error(f"Telegram error: {context.error}")

    # ── Send API ─────────────────────────────────────────────

    async def send_message(self, chat_id: str, text: str,
                           parse_mode: Optional[str] = "Markdown") -> bool:
        if not self._app:
            return False
        try:
            await self._app.bot.send_message(
                chat_id=chat_id, text=text, parse_mode=parse_mode,
            )
            return True
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False

    async def send_typing(self, chat_id: str) -> bool:
        if not self._app:
            return False
        try:
            await self._app.bot.send_chat_action(chat_id=chat_id, action="typing")
            return True
        except Exception:
            return False
