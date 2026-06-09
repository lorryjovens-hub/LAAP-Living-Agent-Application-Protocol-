"""Tests for LAAP Hook System"""
import pytest
from laap.plugins.hooks import HookManager, HookEvent


class TestHookManager:
    def test_register_and_execute(self):
        hm = HookManager()
        results = []

        def test_hook(ctx):
            results.append("executed")
            return "ok"

        hm.register(HookEvent.AGENT_START, test_hook, name="test_hook")
        hook_results = hm.execute(HookEvent.AGENT_START)
        assert len(hook_results) == 1
        assert hook_results[0].success
        assert len(results) == 1

    def test_once_hook(self):
        hm = HookManager()
        count = [0]

        def once_hook(ctx):
            count[0] += 1
            return "done"

        hm.register(HookEvent.SYSTEM_BOOT, once_hook, name="once", once=True)
        hm.execute(HookEvent.SYSTEM_BOOT)
        hm.execute(HookEvent.SYSTEM_BOOT)
        assert count[0] == 1  # Only executed once

    def test_unregister(self):
        hm = HookManager()
        hm.register(HookEvent.AGENT_STOP, lambda ctx: None, name="stop_hook")
        hm.unregister(HookEvent.AGENT_STOP, "stop_hook")
        results = hm.execute(HookEvent.AGENT_STOP)
        assert len(results) == 0

    def test_clear_event(self):
        hm = HookManager()
        hm.register(HookEvent.TOOL_PRE, lambda ctx: None, name="tool_pre")
        hm.clear(HookEvent.TOOL_PRE)
        results = hm.execute(HookEvent.TOOL_PRE)
        assert len(results) == 0

    def test_status(self):
        hm = HookManager()
        hm.register(HookEvent.LLM_PRE, lambda ctx: None, name="llm_pre")
        status = hm.status
        assert "llm:pre" in status
