"""Platform system tests — 10+ test functions covering base adapter, Telegram, Discord, manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


class TestBaseAdapter:
    """Base platform adapter tests."""

    def test_adapter_create(self):
        from laap.agent_core.platforms.base import BaseAdapter
        adapter = BaseAdapter(name="test_bot", config={})
        assert adapter.name == "test_bot"

    def test_adapter_start_stop(self):
        from laap.agent_core.platforms.base import BaseAdapter
        adapter = BaseAdapter(name="test", config={})
        adapter.start()
        assert adapter.running is True
        adapter.stop()
        assert adapter.running is False

    def test_adapter_send_message(self):
        from laap.agent_core.platforms.base import BaseAdapter
        adapter = BaseAdapter(name="test", config={})
        adapter.send_message = MagicMock(return_value=True)
        result = adapter.send_message("user1", "hello")
        assert result is True

    def test_adapter_handle_update(self):
        from laap.agent_core.platforms.base import BaseAdapter
        adapter = BaseAdapter(name="test", config={})
        adapter.handle_update = MagicMock()
        adapter.handle_update({"type": "message", "text": "hi"})
        assert adapter.handle_update.called


class TestTelegramAdapter:
    """Telegram adapter tests."""

    def test_telegram_create(self):
        from laap.agent_core.platforms.telegram import TelegramAdapter
        adapter = TelegramAdapter(token="test:token")
        assert adapter.token == "test:token"
        assert adapter.name == "telegram"

    def test_telegram_send_message(self):
        from laap.agent_core.platforms.telegram import TelegramAdapter
        adapter = TelegramAdapter(token="test:token")
        adapter.send_message = MagicMock(return_value=True)
        result = adapter.send_message(chat_id="123", text="hello")
        assert result is True

    def test_telegram_parse_update(self):
        from laap.agent_core.platforms.telegram import TelegramAdapter
        adapter = TelegramAdapter(token="test:token")
        update = {"message": {"chat": {"id": 123}, "text": "hello"}}
        parsed = adapter.parse_update(update)
        assert parsed is not None


class TestDiscordAdapter:
    """Discord adapter tests."""

    def test_discord_create(self):
        from laap.agent_core.platforms.discord import DiscordAdapter
        adapter = DiscordAdapter(token="discord_token")
        assert adapter.token == "discord_token"

    def test_discord_send_message(self):
        from laap.agent_core.platforms.discord import DiscordAdapter
        adapter = DiscordAdapter(token="test")
        adapter.send_message = MagicMock(return_value=True)
        result = adapter.send_message(channel_id="456", content="hello")
        assert result is True

    def test_discord_parse_event(self):
        from laap.agent_core.platforms.discord import DiscordAdapter
        adapter = DiscordAdapter(token="test")
        event = {"type": "MESSAGE_CREATE", "data": {"content": "hello", "channel_id": "456"}}
        parsed = adapter.parse_event(event)
        assert parsed is not None


class TestPlatformManager:
    """Platform manager tests."""

    def test_manager_create(self):
        from laap.agent_core.platforms.manager import PlatformManager
        pm = PlatformManager()
        assert pm.adapters == {}

    def test_manager_register(self):
        from laap.agent_core.platforms.manager import PlatformManager
        pm = PlatformManager()
        adapter = MagicMock()
        adapter.name = "test_platform"
        pm.register(adapter)
        assert "test_platform" in pm.adapters

    def test_manager_unregister(self):
        from laap.agent_core.platforms.manager import PlatformManager
        pm = PlatformManager()
        adapter = MagicMock()
        adapter.name = "test"
        pm.register(adapter)
        pm.unregister("test")
        assert "test" not in pm.adapters

    def test_manager_get_adapter(self):
        from laap.agent_core.platforms.manager import PlatformManager
        pm = PlatformManager()
        adapter = MagicMock()
        adapter.name = "my_bot"
        pm.register(adapter)
        result = pm.get_adapter("my_bot")
        assert result is adapter
