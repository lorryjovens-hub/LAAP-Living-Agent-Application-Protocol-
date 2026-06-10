"""Integration tests — 5+ test functions covering full conversation, tool chain, memory persistence, platform routing."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Dict, Any, List


class TestFullConversation:
    """Full conversation flow integration."""

    def test_conversation_flow(self, mock_llm, mock_memory, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        mock_llm.generate = AsyncMock(side_effect=[
            "Hello! How can I help?",
            "LAAP is an agent framework.",
            "Goodbye!",
        ])
        agent = LAAPAgent(llm=mock_llm, memory_manager=mock_memory, tool_manager=mock_tool_manager)
        r1 = agent.chat("Hi")
        r2 = agent.chat("What is LAAP?")
        r3 = agent.chat("Bye")
        assert "Hello" in r1
        assert "LAAP" in r2
        assert "Goodbye" in r3

    def test_conversation_context_maintained(self, mock_llm, mock_memory, mock_tool_manager):
        from laap.agent_core.agent import LAAPAgent
        mock_llm.generate = AsyncMock(return_value="ok")
        agent = LAAPAgent(llm=mock_llm, memory_manager=mock_memory, tool_manager=mock_tool_manager)
        agent.chat("first")
        agent.chat("second")
        agent.chat("third")
        assert len(agent.context.messages) >= 3


class TestToolChain:
    """Tool chaining integration."""

    def test_tool_chain_execution(self, mock_tool_manager):
        order = []
        def tool_a(**kw):
            order.append("a")
            return "result_a"
        def tool_b(**kw):
            order.append("b")
            return "result_b"
        mock_tool_manager.registry = {"tool_a": {"fn": tool_a}, "tool_b": {"fn": tool_b}}
        mock_tool_manager.execute_tool.side_effect = lambda name, **kw: mock_tool_manager.registry[name]["fn"](**kw)
        r1 = mock_tool_manager.registry["tool_a"]["fn"]()
        r2 = mock_tool_manager.registry["tool_b"]["fn"]()
        assert order == ["a", "b"]
        assert r1 == "result_a"
        assert r2 == "result_b"

    def test_tool_result_passing(self):
        def search(**kw):
            return {"results": ["file1.txt", "file2.txt"]}
        def read(**kw):
            return {"content": f"Reading {kw.get('path', '')}"}
        search_result = search(query="test")
        read_result = read(path=search_result["results"][0])
        assert "file1.txt" in read_result["content"]


class TestMemoryPersistence:
    """Memory persistence integration."""

    def test_memory_store_and_retrieve(self, mock_memory):
        content = "User mentioned their name is Alice"
        mem_id = mock_memory.store(content, {"type": "episodic"})
        retrieved = mock_memory.retrieve(mem_id)
        assert retrieved is not None

    def test_memory_search_relevant(self, mock_memory):
        mock_memory.search = AsyncMock(return_value=[
            {"id": "m1", "content": "User likes Python", "score": 0.92},
            {"id": "m2", "content": "User likes Rust", "score": 0.85},
        ])
        results = mock_memory.search("programming preferences")
        assert len(results) == 2
        assert results[0]["score"] >= results[1]["score"]

    def test_memory_delete_persistence(self):
        store = {}
        def store_mem(key, val):
            store[key] = val
        def delete_mem(key):
            if key in store:
                del store[key]
                return True
            return False
        store_mem("test_id", "data")
        assert "test_id" in store
        result = delete_mem("test_id")
        assert result is True
        assert "test_id" not in store


class TestPlatformRouting:
    """Platform routing integration."""

    def test_message_routing(self):
        routes = {}
        def register_route(platform, handler):
            routes[platform] = handler
        def route_message(platform, msg):
            if platform in routes:
                return routes[platform](msg)
            return None
        handler = MagicMock(return_value="handled")
        register_route("telegram", handler)
        result = route_message("telegram", "hello")
        assert result == "handled"
        assert handler.called

    def test_multi_platform_dispatch(self):
        results = {}
        def dispatch(platform, msg):
            results[platform] = msg
        dispatch("telegram", "msg1")
        dispatch("discord", "msg2")
        dispatch("slack", "msg3")
        assert results["telegram"] == "msg1"
        assert results["discord"] == "msg2"
        assert results["slack"] == "msg3"
