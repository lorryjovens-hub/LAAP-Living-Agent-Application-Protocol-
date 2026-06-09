"""Stability & Stress Tests for LAAP Core Components

Covers: concurrent access, rapid registration, large inputs,
edge cases, error recovery, and long-running loop safety.
"""
import sys
sys.path.insert(0, r"D:\LAAP")

import json, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from laap.tools.base import Tool, infer_json_schema
from laap.tools.tool_registry import ToolRegistry
from laap.tools.hermes_adapter import HermesAdapter
from laap.ui.stream_handler import StreamHandler, StreamStats, CodeBlockTracker, ThinkingIndicator
from laap.llm.provider import StreamEvent


# ═══════════════════════════════════════════════════════════════
# ToolRegistry — Concurrent Safety
# ═══════════════════════════════════════════════════════════════

def test_registry_concurrent_register():
    """Multiple threads registering tools should not corrupt registry."""
    tr = ToolRegistry()
    errors = []
    lock = threading.Lock()

    def register_tool(i):
        try:
            t = Tool(name=f"concurrent_{i}", description=f"Tool {i}",
                     handler=lambda x=i: x)
            tr.register(t)
        except Exception as e:
            with lock:
                errors.append((i, str(e)))

    with ThreadPoolExecutor(max_workers=20) as ex:
        list(ex.map(register_tool, range(100)))

    assert len(errors) == 0, f"Errors: {errors}"
    assert tr.count == 100
    # Verify all tools accessible
    for i in range(100):
        t = tr.get(f"concurrent_{i}")
        assert t is not None, f"Missing tool {i}"
        assert t.handler() == i


def test_registry_concurrent_get():
    """Concurrent reads should work while registry is populated."""
    tr = ToolRegistry()
    for i in range(50):
        tr.register(Tool(name=f"get_{i}", handler=lambda: i))

    results = []

    def read_tool(i):
        for _ in range(10):
            t = tr.get(f"get_{i}")
            if t is None:
                return f"Missing {i}"
        return None

    with ThreadPoolExecutor(max_workers=10) as ex:
        for r in ex.map(read_tool, range(50)):
            if r:
                results.append(r)

    assert results == [], f"Read errors: {results}"


def test_registry_concurrent_call():
    """Concurrent tool execution should all succeed."""
    tr = ToolRegistry()
    for i in range(20):
        tr.register(Tool(name=f"call_{i}", handler=lambda x=i: x * 2))

    results = set()

    def call_tool(i):
        val = tr.call(f"call_{i}")
        return val

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(call_tool, i) for i in range(20)]
        for f in as_completed(futures):
            results.add(f.result())

    assert results == {i * 2 for i in range(20)}


# ═══════════════════════════════════════════════════════════════
# ToolRegistry — Rapid Registration
# ═══════════════════════════════════════════════════════════════

def test_registry_rapid_register_get():
    """Rapid register/get cycles should be stable."""
    tr = ToolRegistry()
    for i in range(500):
        tr.register(Tool(name=f"rapid_{i}", handler=lambda: i))
        t = tr.get(f"rapid_{i}")
        assert t is not None
        assert t.handler() == i
    assert tr.count == 500


def test_registry_rapid_register_duplicates():
    """Rapid registration of duplicates should not increase count."""
    tr = ToolRegistry()
    for i in range(100):
        t = Tool(name="dup_rapid", handler=lambda: i)
        tr.register(t)
    assert tr.count == 1  # only first registered


# ═══════════════════════════════════════════════════════════════
# ToolRegistry — Edge Cases
# ═══════════════════════════════════════════════════════════════

def test_registry_empty_list():
    """Listing from an empty registry should return empty list."""
    tr = ToolRegistry()
    assert tr.list() == []
    assert tr.list(category="anything") == []
    assert tr.count == 0


def test_registry_call_throws_safe():
    """Handler that raises should return error JSON, not propagate."""
    tr = ToolRegistry()
    def crash(**kw):
        raise RuntimeError("Kaboom!")
    tr.register(Tool(name="crash", handler=crash))
    result = json.loads(tr.call("crash"))
    assert "error" in result
    assert "RuntimeError" in result["error"]


def test_registry_unregister_not_supported():
    """No unregister method — just verify get after losing reference."""
    tr = ToolRegistry()
    tr.register(Tool(name="temp", handler=lambda: "ok"))
    # Overwrite should work via register with overwrite flag
    tr.register(Tool(name="temp", handler=lambda: "new"), overwrite=True)
    assert tr.get("temp").handler() == "new"


# ═══════════════════════════════════════════════════════════════
# HermesAdapter — Edge Cases
# ═══════════════════════════════════════════════════════════════

def test_adapter_sync_empty_registry():
    """Syncing from empty Ao registry should work."""
    tr = ToolRegistry()
    adapter = HermesAdapter(tr)
    count = adapter.sync_from_ao(toolset_filter="__nonexistent__")
    assert count == 0


def test_adapter_push_missing_registry():
    """Pushing from empty LAAP registry should not crash."""
    tr = ToolRegistry()
    adapter = HermesAdapter(tr)
    count = adapter.push_all_to_ao(toolset="test")
    assert count == 0


# ═══════════════════════════════════════════════════════════════
# CodeBlockTracker — Edge Cases
# ═══════════════════════════════════════════════════════════════

def test_code_block_reset():
    """Tracker should handle multiple code blocks sequentially."""
    cbt = CodeBlockTracker()
    cbt.feed("```py")
    assert cbt.in_code_block
    cbt.feed("a")
    cbt.feed("```")
    assert not cbt.in_code_block
    # Second block
    cbt.feed("```js")
    assert cbt.in_code_block
    assert cbt.code_lang == "js"


def test_code_block_partial_markers_all_tokens():
    """Handle ``` split across many tokens."""
    cbt = CodeBlockTracker()
    assert not cbt.feed("`")
    assert not cbt.feed("`")
    assert cbt.feed("`")  # third backtick triggers it
    assert cbt.in_code_block


# ═══════════════════════════════════════════════════════════════
# ThinkingIndicator — Edge Cases
# ═══════════════════════════════════════════════════════════════

def test_thinking_indicator_nested_no_crash():
    """Nested thinking tags should not crash."""
    ti = ThinkingIndicator()
    ti.feed("<thinking>")
    ti.feed("outer")
    ti.feed("<thinking>")
    ti.feed("inner")
    assert ti.in_thinking


def test_thinking_indicator_empty_render():
    """Rendering empty thinking should produce empty string."""
    ti = ThinkingIndicator()
    assert ti.render_thinking_line() == ""


def test_thinking_indicator_long_content():
    """Long thinking content should be truncated in render."""
    ti = ThinkingIndicator()
    ti.thinking_content = "x" * 200
    line = ti.render_thinking_line()
    assert "…" in line  # truncation marker
    assert len(line) < 150  # truncated


# ═══════════════════════════════════════════════════════════════
# StreamHandler — Large Inputs
# ═══════════════════════════════════════════════════════════════

def test_stream_handler_large_content():
    """Process stream with many tokens."""
    handler = StreamHandler(verbose=False)

    def gen():
        for i in range(1000):
            yield StreamEvent(type="token", content=f"tok{i} ")
        yield StreamEvent(type="done", done=True)

    result = handler.process_stream(gen())
    assert handler.stats.token_count == 1000
    assert len(result) > 0

    # Stats should be present
    display = handler.stats.display()
    assert "1000 tok" in display


def test_stream_handler_large_tool_calls():
    """Process stream with many simultaneous tool calls."""
    handler = StreamHandler(verbose=False)

    calls = []
    for i in range(50):
        calls.append({
            "id": f"c{i}",
            "function": {"name": f"tool_{i}", "arguments": '{"x": 1}'},
        })

    def gen():
        yield StreamEvent(type="tool_call_start", tool_call={"calls": calls})
        yield StreamEvent(type="done", done=True)

    handler.process_stream(gen())
    assert len(handler.tool_call_buffer) == 50


# ═══════════════════════════════════════════════════════════════
# StreamStats — Extreme Values
# ═══════════════════════════════════════════════════════════════

def test_stats_zero_tokens():
    """Stats with zero tokens should not crash display."""
    s = StreamStats()
    s.start()
    s.finish()
    display = s.display()
    assert "0 tok" in display


def test_stats_very_high_tps():
    """Very high tokens-per-second should not overflow."""
    s = StreamStats()
    s.start()
    s.first_token_time = s.start_time + 0.0001
    s.token_count = 10000
    s.end_time = s.start_time + 0.5
    assert s.tokens_per_second == 20000.0
    display = s.display()
    assert "20000.0 tok/s" in display


def test_stats_tool_call_count_zero():
    """Zero tool calls should not appear in display."""
    s = StreamStats()
    s.start()
    s.record_token()
    s.finish()
    display = s.display()
    assert "tools" not in display  # no tool section when zero


# ═══════════════════════════════════════════════════════════════
# Error Recovery
# ═══════════════════════════════════════════════════════════════

def test_stream_handler_reset_after_error():
    """Reset after error should clear all state."""
    handler = StreamHandler(verbose=False)

    def failing_gen():
        ev = StreamEvent(type="error")
        ev.error = "fail"
        yield ev

    try:
        handler.process_stream(failing_gen(), max_retries=0)
    except IOError:
        pass

    assert handler.has_errors
    assert handler.last_error is not None

    handler.reset()
    assert handler.content == ""
    assert not handler.has_errors
    assert handler.stats.token_count == 0


# ═══════════════════════════════════════════════════════════════
# Long-Running Loop Safety
# ═══════════════════════════════════════════════════════════════

def test_registry_many_categories():
    """Many categories should not degrade performance."""
    tr = ToolRegistry()
    for i in range(100):
        tr.register(Tool(name=f"ct_{i}", category=f"cat_{i % 10}",
                         handler=lambda: i))

    assert tr.count == 100
    assert len(tr.categories) == 10


def test_registry_call_nonexistent_safe():
    """Calling many nonexistent tools should not crash."""
    tr = ToolRegistry()
    for i in range(100):
        result = tr.call(f"no_such_{i}")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "not found" in parsed["error"]


# ═══════════════════════════════════════════════════════════════
# Tool Base — Extreme Schema Inference
# ═══════════════════════════════════════════════════════════════

def test_schema_many_parameters():
    """infer_json_schema with many parameters should not degrade."""
    hints = {f"param_{i}": str for i in range(100)}
    schema = infer_json_schema(hints)
    assert len(schema["properties"]) == 100
    assert len(schema["required"]) == 100


def test_schema_all_types():
    """All supported types should be inferred correctly."""
    from typing import Optional, List, Dict
    hints = {
        "s": str,
        "i": int,
        "f": float,
        "b": bool,
        "d": dict,
        "l": list,
        "os": Optional[str],
    }
    schema = infer_json_schema(hints)
    assert schema["properties"]["s"]["type"] == "string"
    assert schema["properties"]["i"]["type"] == "integer"
    assert schema["properties"]["f"]["type"] == "number"
    assert schema["properties"]["b"]["type"] == "boolean"
    assert schema["properties"]["d"]["type"] == "object"
    assert schema["properties"]["l"]["type"] == "array"
    # Optional[str] should not be required
    assert "os" not in schema["required"]


# ═══════════════════════════════════════════════════════════════
# Async Stream — Concurrent Safety
# ═══════════════════════════════════════════════════════════════

def test_async_stream_large():
    """Async stream with many tokens should complete."""
    import asyncio
    handler = StreamHandler(verbose=False)

    async def large_gen():
        for i in range(500):
            yield StreamEvent(type="token", content=f"{i} ")
        yield StreamEvent(type="done", done=True)

    result = asyncio.run(handler.async_process_stream(large_gen()))
    assert handler.stats.token_count == 500
    assert len(result) > 0


# ═══════════════════════════════════════════════════════════════
# Quick throughput test
# ═══════════════════════════════════════════════════════════════

def test_rapid_handler_create():
    """Creating and discarding many handlers should be safe."""
    for _ in range(100):
        handler = StreamHandler(verbose=False)
        assert not handler._stopped
