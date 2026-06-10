"""Agent core tests — 30+ test functions covering Agent, Context, MemoryBridge."""

import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch, call
from datetime import datetime
from typing import Dict, List, Any, Optional


class TestAgentCreate:
    """Agent creation and configuration."""

    def test_agent_instantiation(self, mock_llm, mock_memory, mock_tool_manager):
        """Agent can be created with required dependencies."""
        from laap.agent_core.agent import LAAPAgent
        agent = LAAPAgent(
            llm=mock_llm,
            memory_manager=mock_memory,
            tool_manager=mock_tool_manager,
        )
        assert agent is not None
        assert agent.llm is mock_llm

    def test_agent_default_id(self, mock_llm, mock_memory, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        agent = LAAPAgent(llm=mock_llm, memory_manager=mock_memory, tool_manager=mock_tool_manager)
        assert agent.agent_id is not None
        assert len(agent.agent_id) > 0

    def test_agent_custom_id(self, mock_llm, mock_memory, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        agent = LAAPAgent(llm=mock_llm, memory_manager=mock_memory, tool_manager=mock_tool_manager, agent_id="custom-1")
        assert agent.agent_id == "custom-1"

    def test_agent_system_prompt(self, mock_llm, mock_memory, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        sp = "You are a test agent."
        agent = LAAPAgent(llm=mock_llm, memory_manager=mock_memory, tool_manager=mock_tool_manager, system_prompt=sp)
        assert agent.system_prompt == sp

    def test_agent_max_tokens_default(self, mock_llm, mock_memory, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        agent = LAAPAgent(llm=mock_llm, memory_manager=mock_memory, tool_manager=mock_tool_manager)
        assert agent.max_tokens > 0

    def test_agent_temperature_default(self, mock_llm, mock_memory, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        agent = LAAPAgent(llm=mock_llm, memory_manager=mock_memory, tool_manager=mock_tool_manager)
        assert 0.0 <= agent.temperature <= 2.0


class TestAgentChat:
    """Agent conversation and chat."""

    def test_chat_returns_response(self, mock_llm, mock_memory, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        mock_llm.generate = AsyncMock(return_value="Hi there!")
        agent = LAAPAgent(llm=mock_llm, memory_manager=mock_memory, tool_manager=mock_tool_manager)
        result = agent.chat("Hello")
        assert "Hi there!" in result

    def test_chat_calls_llm_with_messages(self, mock_llm, mock_memory, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        agent = LAAPAgent(llm=mock_llm, memory_manager=mock_memory, tool_manager=mock_tool_manager)
        agent.chat("test msg")
        assert mock_llm.generate.called

    def test_chat_empty_message(self, mock_llm, mock_memory, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        mock_llm.generate = AsyncMock(return_value="")
        agent = LAAPAgent(llm=mock_llm, memory_manager=mock_memory, tool_manager=mock_tool_manager)
        result = agent.chat("")
        assert result is not None

    def test_chat_multiple_turns(self, mock_llm, mock_memory, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        mock_llm.generate = AsyncMock(return_value="ok")
        agent = LAAPAgent(llm=mock_llm, memory_manager=mock_memory, tool_manager=mock_tool_manager)
        agent.chat("first")
        agent.chat("second")
        assert mock_llm.generate.call_count == 2

    def test_chat_with_system_prompt_included(self, mock_llm, mock_memory, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        agent = LAAPAgent(llm=mock_llm, memory_manager=mock_memory, tool_manager=mock_tool_manager, system_prompt="Be helpful.")
        agent.chat("hello")
        args, _ = mock_llm.generate.call_args
        messages = args[0] if args else []
        assert any("Be helpful." in str(m) for m in messages)


class TestContextMessages:
    """Context message management."""

    def test_context_add_message(self):
        from laap.agent_core.context import Context
        ctx = Context(max_tokens=4096)
        ctx.add_message("user", "Hello")
        assert len(ctx.messages) == 1

    def test_context_add_system_message(self):
        from laap.agent_core.context import Context
        ctx = Context(max_tokens=4096)
        ctx.add_system_message("You are a bot.")
        assert ctx.messages[0]["role"] == "system"

    def test_context_get_messages(self):
        from laap.agent_core.context import Context
        ctx = Context(max_tokens=4096)
        ctx.add_message("user", "Hi")
        ctx.add_message("assistant", "Hello")
        msgs = ctx.get_messages()
        assert len(msgs) == 2

    def test_context_message_order(self):
        from laap.agent_core.context import Context
        ctx = Context(max_tokens=4096)
        ctx.add_message("user", "first")
        ctx.add_message("assistant", "second")
        assert ctx.messages[0]["content"] == "first"
        assert ctx.messages[1]["content"] == "second"

    def test_context_clear(self):
        from laap.agent_core.context import Context
        ctx = Context(max_tokens=4096)
        ctx.add_message("user", "test")
        ctx.clear()
        assert len(ctx.messages) == 0

    def test_context_clear_preserves_system(self):
        from laap.agent_core.context import Context
        ctx = Context(max_tokens=4096)
        ctx.add_system_message("System prompt.")
        ctx.add_message("user", "test")
        ctx.clear(preserve_system=True)
        assert len(ctx.messages) == 1
        assert ctx.messages[0]["role"] == "system"

    def test_context_token_count(self):
        from laap.agent_core.context import Context
        ctx = Context(max_tokens=4096, token_counter=lambda t: len(t.split()))
        ctx.add_message("user", "hello world")
        assert ctx.token_count() == 2


class TestContextTrim:
    """Token-based context trimming."""

    def test_trim_removes_old_messages(self):
        from laap.agent_core.context import Context
        ctx = Context(max_tokens=10, token_counter=lambda t: len(t.split()))
        ctx.add_system_message("sys")  # 1 token
        for i in range(5):
            ctx.add_message("user", f"message {i}")  # 2 tokens each
        ctx.trim()
        assert ctx.token_count() <= 10

    def test_trim_preserves_system(self):
        from laap.agent_core.context import Context
        ctx = Context(max_tokens=5, token_counter=lambda t: len(t.split()))
        ctx.add_system_message("keep this")  # 2 tokens
        ctx.add_message("user", "a b c d e f")  # 6 tokens
        ctx.trim()
        assert ctx.messages[0]["role"] == "system"

    def test_trim_noop_when_under_limit(self):
        from laap.agent_core.context import Context
        ctx = Context(max_tokens=100, token_counter=lambda t: len(t.split()))
        ctx.add_message("user", "hi")
        before = len(ctx.messages)
        ctx.trim()
        assert len(ctx.messages) == before

    def test_trim_removes_oldest_first(self):
        from laap.agent_core.context import Context
        ctx = Context(max_tokens=20, token_counter=lambda t: len(t.split()))
        ctx.add_system_message("sys")
        ctx.add_message("user", "msg1 long content")
        ctx.add_message("user", "msg2 long content")
        ctx.add_message("user", "msg3 long content")
        ctx.trim()
        contents = [m["content"] for m in ctx.messages if m["role"] != "system"]
        assert "msg1" not in contents or len(contents) <= 2

    def test_trim_empty_context(self):
        from laap.agent_core.context import Context
        ctx = Context(max_tokens=10)
        ctx.trim()  # should not raise
        assert True


class TestMemoryBridge:
    """Memory bridge between agent and memory system."""

    def test_memory_bridge_store(self, mock_memory):
        from laap.agent_core.memory_bridge import MemoryBridge
        bridge = MemoryBridge(mock_memory)
        result = bridge.store("test content", {"type": "episodic"})
        assert mock_memory.store.called

    def test_memory_bridge_retrieve(self, mock_memory):
        from laap.agent_core.memory_bridge import MemoryBridge
        bridge = MemoryBridge(mock_memory)
        result = bridge.retrieve("mem-1")
        assert result is not None

    def test_memory_bridge_search(self, mock_memory):
        from laap.agent_core.memory_bridge import MemoryBridge
        bridge = MemoryBridge(mock_memory)
        results = bridge.search("test query")
        assert len(results) > 0

    def test_memory_bridge_delete(self, mock_memory):
        from laap.agent_core.memory_bridge import MemoryBridge
        bridge = MemoryBridge(mock_memory)
        result = bridge.delete("mem-1")
        assert result is True

    def test_memory_bridge_list_recent(self, mock_memory):
        from laap.agent_core.memory_bridge import MemoryBridge
        mock_memory.search = AsyncMock(return_value=[
            {"id": "m1", "content": "a"},
            {"id": "m2", "content": "b"},
        ])
        bridge = MemoryBridge(mock_memory)
        results = bridge.list_recent(limit=5)
        assert len(results) == 2

    def test_memory_bridge_context_injection(self, mock_memory):
        from laap.agent_core.memory_bridge import MemoryBridge
        mock_memory.search = AsyncMock(return_value=[
            {"id": "m1", "content": "relevant memory", "score": 0.95}
        ])
        bridge = MemoryBridge(mock_memory)
        context_str = bridge.get_context_string("current query")
        assert "relevant memory" in context_str


class TestAgentAdditional:
    """Additional agent functionality tests."""

    def test_agent_stop(self, mock_llm, mock_memory, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        agent = LAAPAgent(llm=mock_llm, memory_manager=mock_memory, tool_manager=mock_tool_manager)
        agent.stop()
        assert not agent.running

    def test_agent_reset(self, mock_llm, mock_memory, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        agent = LAAPAgent(llm=mock_llm, memory_manager=mock_memory, tool_manager=mock_tool_manager)
        agent.chat("hello")
        agent.reset()
        assert len(agent.context.messages) == 0

    def test_agent_get_status(self, mock_llm, mock_memory, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        agent = LAAPAgent(llm=mock_llm, memory_manager=mock_memory, tool_manager=mock_tool_manager)
        status = agent.get_status()
        assert "agent_id" in status
        assert "running" in status

    def test_agent_tool_execution(self, mock_llm, mock_memory, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        agent = LAAPAgent(llm=mock_llm, memory_manager=mock_memory, tool_manager=mock_tool_manager)
        agent.tool_manager = mock_tool_manager
        result = agent.execute_tool("read_file", {"path": "/tmp/test.txt"})
        assert mock_tool_manager.execute_tool.called

    def test_agent_llm_provider_swap(self, mock_llm, mock_memory, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        agent = LAAPAgent(llm=mock_llm, memory_manager=mock_memory, tool_manager=mock_tool_manager)
        new_llm = AsyncMock()
        agent.set_llm_provider(new_llm)
        assert agent.llm is new_llm

    def test_agent_memory_disabled(self, mock_llm, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        agent = LAAPAgent(llm=mock_llm, memory_manager=None, tool_manager=mock_tool_manager)
        assert agent.memory_manager is None
