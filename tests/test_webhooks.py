"""Tests for webhook manager and commands."""
import pytest
import json
import os
import tempfile
from pathlib import Path


class TestWebhookManager:
    """Test WebhookManager CRUD operations."""

    @pytest.fixture
    def manager(self):
        from laap.gateway.webhooks import WebhookManager
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            mgr = WebhookManager(config_path)
            yield mgr

    def test_subscribe(self, manager):
        sub = manager.subscribe("test-webhook", "https://example.com/hook")
        assert sub["name"] == "test-webhook"
        assert sub["url"] == "https://example.com/hook"
        assert sub["event_type"] == "*"
        assert "created_at" in sub

    def test_subscribe_custom_event(self, manager):
        sub = manager.subscribe("event-webhook", "https://example.com/hook2", event_type="push")
        assert sub["event_type"] == "push"

    def test_list(self, manager):
        manager.subscribe("hook1", "https://a.com")
        manager.subscribe("hook2", "https://b.com")
        subs = manager.list()
        assert len(subs) == 2

    def test_list_empty(self, manager):
        assert manager.list() == []

    def test_get(self, manager):
        manager.subscribe("test-hook", "https://example.com")
        sub = manager.get("test-hook")
        assert sub is not None
        assert sub["name"] == "test-hook"
        assert "secret" not in sub  # secrets excluded from get()

    def test_get_nonexistent(self, manager):
        assert manager.get("no-such-hook") is None

    def test_remove(self, manager):
        manager.subscribe("to-remove", "https://example.com")
        assert manager.remove("to-remove") is True
        assert manager.get("to-remove") is None

    def test_remove_nonexistent(self, manager):
        from laap.gateway.webhooks import WebhookNotFoundError
        with pytest.raises(WebhookNotFoundError):
            manager.remove("no-such-hook")

    def test_trigger_no_matches(self, manager):
        results = manager.trigger("push", {"data": "test"})
        assert results == []

    def test_trigger_matches_event(self, manager):
        manager.subscribe("push-hook", "https://example.com", event_type="push")
        results = manager.trigger("push", {"data": "test"})
        assert len(results) == 1
        # Delivery may fail (no real server), but it should have been attempted
        assert results[0]["name"] == "push-hook"

    def test_trigger_wildcard(self, manager):
        manager.subscribe("wildcard-hook", "https://example.com", event_type="*")
        results = manager.trigger("anything", {"data": "test"})
        assert len(results) == 1

    def test_trigger_skips_inactive(self, manager):
        mgr = manager
        mgr.subscribe("active", "https://a.com")
        mgr.subscribe("inactive", "https://b.com")
        # Manually deactivate
        mgr._subs()["inactive"]["active"] = False
        mgr._save()
        results = mgr.trigger("*", {"data": "test"})
        names = [r["name"] for r in results]
        assert "active" in names
        assert "inactive" not in names

    def test_sign_and_verify(self, manager):
        from laap.gateway.webhooks import WebhookManager as WM
        body = b'{"test": true}'
        sig = WM._sign("mysecret", body)
        assert WM.verify_signature("mysecret", body, sig) is True
        assert WM.verify_signature("mysecret", b'{"test": false}', sig) is False
        assert WM.verify_signature("wrongsecret", body, sig) is False

    def test_persistence(self, manager):
        path = manager.config_path
        mgr1 = manager
        mgr1.subscribe("persistent", "https://example.com")
        del mgr1

        mgr2 = __import__("laap.gateway.webhooks", fromlist=["WebhookManager"]).WebhookManager(path)
        sub = mgr2.get("persistent")
        assert sub is not None
        assert sub["name"] == "persistent"
