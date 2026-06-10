"""Plugin system tests — 10+ test functions covering hooks, manager, context plugins."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


class TestHookRegistry:
    """Hook registration tests."""

    def test_hook_registry_create(self):
        from laap.agent_core.plugins.hooks import HookRegistry
        hr = HookRegistry()
        assert hr.hooks == {}

    def test_hook_register(self):
        from laap.agent_core.plugins.hooks import HookRegistry
        hr = HookRegistry()
        fn = MagicMock()
        hr.register("pre_process", fn)
        assert "pre_process" in hr.hooks
        assert fn in hr.hooks["pre_process"]

    def test_hook_register_multiple(self):
        from laap.agent_core.plugins.hooks import HookRegistry
        hr = HookRegistry()
        hr.register("event1", MagicMock())
        hr.register("event1", MagicMock())
        assert len(hr.hooks["event1"]) == 2

    def test_hook_unregister(self):
        from laap.agent_core.plugins.hooks import HookRegistry
        hr = HookRegistry()
        fn = MagicMock()
        hr.register("test", fn)
        hr.unregister("test", fn)
        assert fn not in hr.hooks["test"]

    def test_hook_list(self):
        from laap.agent_core.plugins.hooks import HookRegistry
        hr = HookRegistry()
        hr.register("a", MagicMock())
        hr.register("b", MagicMock())
        names = hr.list_hooks()
        assert "a" in names
        assert "b" in names


class TestHookTrigger:
    """Hook triggering tests."""

    def test_hook_trigger(self):
        from laap.agent_core.plugins.hooks import HookRegistry
        hr = HookRegistry()
        fn = MagicMock()
        hr.register("pre_process", fn)
        hr.trigger("pre_process", data={"msg": "hello"})
        fn.assert_called_once()

    def test_hook_trigger_nonexistent(self):
        from laap.agent_core.plugins.hooks import HookRegistry
        hr = HookRegistry()
        hr.trigger("unknown", data={})  # should not raise
        assert True

    def test_hook_trigger_order(self):
        from laap.agent_core.plugins.hooks import HookRegistry
        hr = HookRegistry()
        order = []
        hr.register("test", lambda d: order.append(1), priority=10)
        hr.register("test", lambda d: order.append(2), priority=5)
        hr.trigger("test", {})
        assert order == [2, 1]


class TestPluginManager:
    """Plugin manager tests."""

    def test_plugin_manager_create(self):
        from laap.agent_core.plugins.manager import PluginManager
        pm = PluginManager()
        assert pm.plugins == {}

    def test_plugin_load(self):
        from laap.agent_core.plugins.manager import PluginManager
        pm = PluginManager()
        plugin = MagicMock()
        plugin.name = "test_plugin"
        pm.load(plugin)
        assert "test_plugin" in pm.plugins
        assert pm.plugins["test_plugin"] is plugin

    def test_plugin_unload(self):
        from laap.agent_core.plugins.manager import PluginManager
        pm = PluginManager()
        plugin = MagicMock()
        plugin.name = "test"
        pm.load(plugin)
        pm.unload("test")
        assert "test" not in pm.plugins

    def test_plugin_list(self):
        from laap.agent_core.plugins.manager import PluginManager
        pm = PluginManager()
        p1 = MagicMock(); p1.name = "p1"
        p2 = MagicMock(); p2.name = "p2"
        pm.load(p1)
        pm.load(p2)
        names = pm.list_plugins()
        assert "p1" in names
        assert "p2" in names


class TestContextPlugin:
    """Context plugin tests."""

    def test_context_plugin_init(self):
        from laap.agent_core.plugins.context_engine import ContextPlugin
        cp = ContextPlugin()
        assert cp is not None

    def test_context_plugin_process(self):
        from laap.agent_core.plugins.context_engine import ContextPlugin
        cp = ContextPlugin()
        result = cp.process({"role": "user", "content": "hello"})
        assert result is not None

    def test_context_plugin_enhance(self):
        from laap.agent_core.plugins.context_engine import ContextPlugin
        cp = ContextPlugin()
        enhanced = cp.enhance("test input")
        assert enhanced is not None
