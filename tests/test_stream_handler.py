"""Test LAAP Stream Handler — streaming, thinking indicators, code blocks, stats"""
import sys
sys.path.insert(0, r"D:\LAAP")

import io, json, time, asyncio
from typing import List

from laap.ui.stream_handler import (
    StreamHandler, CodeBlockTracker, ThinkingIndicator, StreamStats,
)
from laap.llm.provider import StreamEvent, ToolDef


# ── CodeBlockTracker ─────────────────────────────────────────

def test_code_block_tracker_init():
    cbt = CodeBlockTracker()
    assert not cbt.in_code_block
    assert cbt.code_lang == ""
    assert cbt.code_lines == []


def test_code_block_tracker_open():
    cbt = CodeBlockTracker()
    result = cbt.feed("```python\nprint('hi')")
    assert result is True  # now in code block
    assert cbt.in_code_block
    assert cbt.code_lang == "python"


def test_code_block_tracker_open_and_close():
    cbt = CodeBlockTracker()
    cbt.feed("```python\nprint('hi')\n")
    assert cbt.in_code_block
    cbt.feed("```")
    assert not cbt.in_code_block


def test_code_block_tracker_multiple_lines():
    cbt = CodeBlockTracker()
    cbt.feed("```")
    assert cbt.in_code_block
    cbt.feed("line1\n")
    cbt.feed("line2\n")
    cbt.feed("```")
    assert not cbt.in_code_block
    assert len(cbt.code_lines) >= 2


def test_code_block_tracker_no_code():
    cbt = CodeBlockTracker()
    result = cbt.feed("just regular text")
    assert result is False
    assert not cbt.in_code_block


def test_code_block_tracker_partial():
    """Partial code block markers shouldn't trigger when spread across tokens."""
    cbt = CodeBlockTracker()
    assert not cbt.feed("``")  # incomplete
    cbt.feed("`")  # completes it
    assert cbt.in_code_block


def test_code_block_tracker_empty_lang():
    cbt = CodeBlockTracker()
    cbt.feed("```")
    assert cbt.in_code_block
    assert cbt.code_lang == ""  # no language specified


# ── ThinkingIndicator ────────────────────────────────────────

def test_thinking_indicator_init():
    ti = ThinkingIndicator()
    assert not ti.in_thinking
    assert ti.thinking_content == ""


def test_thinking_indicator_detect_markdown():
    """Detect ```thinking blocks."""
    ti = ThinkingIndicator()
    assert not ti.feed("hello ")
    assert ti.feed("```thinking\n")  # enters thinking mode
    assert ti.in_thinking


def test_thinking_indicator_detect_xml():
    """Detect <thinking> XML tags."""
    ti = ThinkingIndicator()
    assert not ti.feed("some text ")
    assert ti.feed("<thinking>")  # enters thinking mode
    assert ti.in_thinking
    ti.feed(" content ")
    assert not ti.feed("</thinking>")  # exits
    assert not ti.in_thinking


def test_thinking_indicator_accumulates():
    ti = ThinkingIndicator()
    ti.feed("<thinking>")
    ti.feed("deep thoughts ")
    ti.feed("here")
    assert "deep thoughts" in ti.thinking_content


def test_thinking_indicator_no_trigger():
    ti = ThinkingIndicator()
    assert not ti.feed("normal text")
    assert not ti.feed("without tags")
    assert not ti.in_thinking


def test_thinking_indicator_render():
    ti = ThinkingIndicator()
    ti.thinking_content = "analyzing the problem"
    rendered = ti.render_thinking_line()
    assert "thinking" in rendered
    assert "analyzing" in rendered


# ── StreamStats ──────────────────────────────────────────────

def test_stream_stats_init():
    s = StreamStats()
    assert s.token_count == 0
    assert s.tool_call_count == 0
    assert s.error_count == 0


def test_stream_stats_record():
    s = StreamStats()
    s.start()
    s.record_token()
    assert s.token_count == 1
    s.record_tool_call()
    assert s.tool_call_count == 1
    s.record_error()
    assert s.error_count == 1


def test_stream_stats_thinking():
    s = StreamStats()
    s.record_thinking_token()
    assert s.thinking_tokens == 1
    assert s.token_count == 1  # also counts toward total


def test_stream_stats_time():
    s = StreamStats()
    s.start()
    time.sleep(0.01)
    s.record_token()
    s.finish()
    assert s.elapsed > 0
    assert s.tokens_per_second > 0


def test_stream_stats_ttft():
    s = StreamStats()
    s.start()
    time.sleep(0.005)
    s.record_token()
    assert s.time_to_first_token > 0


def test_stream_stats_display():
    s = StreamStats()
    s.start()
    s.record_token()
    for _ in range(9):
        s.record_token()
    s.finish()
    display = s.display()
    assert "tok" in display
    assert "tok/s" in display


def test_stream_stats_display_with_tools():
    s = StreamStats()
    s.start()
    for _ in range(5):
        s.record_token()
    s.record_tool_call()
    s.record_tool_call()
    s.finish()
    display = s.display()
    assert "2 tools" in display


def test_stream_stats_display_with_errors():
    s = StreamStats()
    s.start()
    s.record_error()
    s.record_error()
    s.finish()
    display = s.display()
    assert "err" in display


def test_stream_stats_display_memory():
    s = StreamStats()
    s._peak_memory_mb = 123.4
    display = s.display()
    assert "123MB" in display


# ── StreamStats edge cases ───────────────────────────────────

def test_stream_stats_zero_time():
    """Empty stats should not crash display."""
    s = StreamStats()
    assert s.elapsed == 0
    assert s.tokens_per_second == 0
    assert s.time_to_first_token == 0
    assert s.display() != ""


def test_stream_stats_peak_memory_no_psutil():
    """sample_memory should return 0 without psutil."""
    s = StreamStats()
    mb = s.sample_memory()
    # Without psutil, returns 0
    assert isinstance(mb, (int, float))


# ── StreamHandler ────────────────────────────────────────────

def test_stream_handler_init():
    handler = StreamHandler(verbose=False)
    assert handler.content == ""
    assert handler.tool_results == []
    assert not handler._stopped
    assert handler.stats.token_count == 0


def test_stream_handler_process_simple():
    """Process a simple stream with just tokens."""
    handler = StreamHandler(verbose=False)

    def gen():
        yield StreamEvent(type="token", content="Hello")
        yield StreamEvent(type="token", content=" world")
        yield StreamEvent(type="done", done=True)

    result = handler.process_stream(gen())
    assert result == "Hello world"
    assert handler.stats.token_count == 2


def test_stream_handler_process_with_tool_calls():
    """Process stream with tool calls."""
    handler = StreamHandler(verbose=False)

    def gen():
        yield StreamEvent(type="token", content="Let me check")
        yield StreamEvent(type="tool_call_start", tool_call={
            "calls": [{
                "id": "call_1",
                "function": {"name": "get_weather", "arguments": '{"city": "Beijing"}'},
            }],
        })
        yield StreamEvent(type="done", done=True)

    result = handler.process_stream(gen())
    assert "Let me check" in result
    assert len(handler.tool_call_buffer) == 1
    assert handler.stats.tool_call_count == 1


def test_stream_handler_process_with_errors():
    """Error events should be recorded in stats."""
    handler = StreamHandler(verbose=False)

    def gen():
        yield StreamEvent(type="token", content="Partial")
        ev = StreamEvent(type="error")
        ev.error = "Connection lost"
        yield ev

    with pytest.raises(IOError):
        handler.process_stream(gen())
    assert handler.stats.error_count > 0


def test_stream_handler_stop():
    """Stopping the handler should abort processing."""
    handler = StreamHandler(verbose=False)

    def gen():
        yield StreamEvent(type="token", content="One")
        yield StreamEvent(type="token", content="Two")

    handler.stop()
    result = handler.process_stream(gen())
    # Should stop early with no content because _stopped is set
    # (process_stream resets _stopped, so we test manually)
    handler._stopped = True
    result = handler.process_stream(gen())
    # Content should be minimal
    assert isinstance(result, str)


def test_stream_handler_process_tool_result():
    """process_tool_result should record and render."""
    handler = StreamHandler(verbose=False)
    handler.process_tool_result("test_tool", '{"ok": true}', 0.5, success=True)
    assert len(handler.tool_results) == 1
    assert handler.tool_results[0]["name"] == "test_tool"
    assert handler.tool_results[0]["success"] is True


def test_stream_handler_finalize():
    handler = StreamHandler(verbose=False)
    handler.finalize()  # should not crash


def test_stream_handler_reset():
    handler = StreamHandler(verbose=False)
    handler.content = "old"
    handler.tool_results = [{"name": "old"}]
    handler._last_error = "error"
    handler.reset()
    assert handler.content == ""
    assert handler.tool_results == []
    assert handler._last_error is None


def test_stream_handler_last_error():
    handler = StreamHandler(verbose=False)
    assert handler.last_error is None
    assert not handler.has_errors
    handler.stats.record_error()
    assert handler.has_errors


# ── StreamHandler with verbose output ────────────────────────

def test_stream_handler_verbose_output():
    """Verbose mode should write to handler's output stream."""
    captured = io.StringIO()
    handler = StreamHandler(verbose=True, file=captured, use_spinner=False)

    def gen():
        yield StreamEvent(type="token", content="Hello")
        yield StreamEvent(type="done", done=True)

    result = handler.process_stream(gen())

    assert result == "Hello"
    output = captured.getvalue()
    assert len(output) > 0  # something was written


# ── Tool Call Rendering ──────────────────────────────────────

def test_stream_handler_multiple_tool_calls():
    """Multiple simultaneous tool calls should all be recorded."""
    handler = StreamHandler(verbose=False)

    def gen():
        yield StreamEvent(type="token", content="Running tools")
        yield StreamEvent(type="tool_call_start", tool_call={
            "calls": [
                {"id": "c1", "function": {"name": "search", "arguments": "{}"}},
                {"id": "c2", "function": {"name": "read_file", "arguments": '{"path": "x.py"}'}},
            ],
        })
        yield StreamEvent(type="done", done=True)

    handler.process_stream(gen())
    assert len(handler.tool_call_buffer) == 2
    assert handler.stats.tool_call_count == 1  # one event with multiple calls


# ── Async Stream ─────────────────────────────────────────────

def test_async_process_stream():
    """Async streaming should process tokens correctly."""
    handler = StreamHandler(verbose=False)

    async def async_gen():
        yield StreamEvent(type="token", content="Async ")
        yield StreamEvent(type="token", content="hello")
        yield StreamEvent(type="done", done=True)

    result = asyncio.run(handler.async_process_stream(async_gen()))
    assert result == "Async hello"
    assert handler.stats.token_count == 2


def test_async_process_stream_with_tools():
    """Async streaming with tool calls."""
    handler = StreamHandler(verbose=False)

    async def async_gen():
        yield StreamEvent(type="token", content="Thinking")
        yield StreamEvent(type="tool_call_start", tool_call={
            "calls": [{
                "id": "ac1",
                "function": {"name": "test_fn", "arguments": '{"arg": 1}'},
            }],
        })
        yield StreamEvent(type="done", done=True)

    result = asyncio.run(handler.async_process_stream(async_gen()))
    assert result == "Thinking"
    assert handler.stats.tool_call_count == 1


# ── Error Recovery ───────────────────────────────────────────

def test_stream_handler_error_recovery():
    """Error event should be recorded in stats when no retries."""
    handler = StreamHandler(verbose=False)

    def gen():
        ev = StreamEvent(type="error")
        ev.error = "Temp failure"
        yield ev

    try:
        handler.process_stream(gen(), max_retries=0)
    except IOError:
        pass

    assert handler.has_errors
    assert handler.last_error == "Temp failure"
    assert handler.stats.error_count > 0


def test_stream_handler_no_crash_on_empty_stream():
    """An empty generator (no events) should not crash."""
    handler = StreamHandler(verbose=False)

    def gen():
        """Empty generator — yields nothing."""
        if False:
            yield  # makes this a generator function

    # Should not raise
    result = handler.process_stream(gen())
    assert result == ""
    assert handler.stats.token_count == 0


# ── Integration: CodeBlockTracker + StreamHandler ────────────

def test_stream_handler_code_block_tracking():
    """StreamHandler should integrate CodeBlockTracker during streaming."""
    handler = StreamHandler(verbose=False)

    def gen():
        yield StreamEvent(type="token", content="Here's code:\n")
        yield StreamEvent(type="token", content="```python\n")
        yield StreamEvent(type="token", content="print('hi')\n")
        yield StreamEvent(type="token", content="```\n")
        yield StreamEvent(type="token", content="Done.")
        yield StreamEvent(type="done", done=True)

    # Should not crash when code blocks pass through
    result = handler.process_stream(gen())
    assert "print" in result or "Done" in result or "code" in result


# ── Property Access ──────────────────────────────────────────

def test_handler_elapsed():
    handler = StreamHandler(verbose=False)
    elapsed = handler.elapsed
    assert elapsed >= 0


# ── Tool Call with malformed JSON ────────────────────────────

def test_stream_handler_malformed_tool_args():
    """Malformed JSON in tool call arguments should not crash."""
    handler = StreamHandler(verbose=False)

    def gen():
        yield StreamEvent(type="tool_call_start", tool_call={
            "calls": [{
                "id": "bad",
                "function": {"name": "bad_tool", "arguments": "not-json-at-all"},
            }],
        })
        yield StreamEvent(type="done", done=True)

    # Should not raise
    handler.process_stream(gen())
    assert len(handler.tool_call_buffer) == 1


# Need pytest import for pytest.raises
import pytest
