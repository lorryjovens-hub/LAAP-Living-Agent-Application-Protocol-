"""Tests for session_search tool."""
import pytest
import json
import os
from pathlib import Path


class TestSessionSearchTool:
    """Test session search tool functions."""

    def test_search_sessions_no_results(self):
        """search_sessions returns empty when no sessions exist."""
        from laap.tools.session_search import search_sessions
        result = json.loads(search_sessions("nonexistent_query_xyz", limit=1))
        assert isinstance(result, dict)
        assert "results" in result
        assert result["count"] == 0

    def test_search_messages_no_results(self):
        """search_messages returns empty when no matches exist."""
        from laap.tools.session_search import search_messages
        result = json.loads(search_messages("nonexistent_xyz789"))
        assert isinstance(result, dict)
        assert "results" in result

    def test_get_session_nonexistent(self):
        """get_session handles non-existent session gracefully."""
        from laap.tools.session_search import get_session
        result = json.loads(get_session("no_such_session_999"))
        assert isinstance(result, dict)
        assert "session" in result
        assert "messages" in result

    def test_tool_definitions_structure(self):
        """TOOL_DEFINITIONS has correct structure."""
        from laap.tools.session_search import TOOL_DEFINITIONS
        assert "search_sessions" in TOOL_DEFINITIONS
        assert "search_messages" in TOOL_DEFINITIONS
        assert "get_session" in TOOL_DEFINITIONS
        for name, tdef in TOOL_DEFINITIONS.items():
            assert "name" in tdef
            assert "description" in tdef
            assert "parameters" in tdef
            assert "handler" in tdef
            assert "properties" in tdef["parameters"]
            assert "required" in tdef["parameters"]

    def test_tool_handlers_callable(self):
        """Each tool definition has a callable handler."""
        from laap.tools.session_search import TOOL_DEFINITIONS
        for name, tdef in TOOL_DEFINITIONS.items():
            handler = tdef["handler"]
            assert callable(handler), f"Handler for {name} is not callable"

    def test_search_sessions_handler(self):
        """Handler can be called with args dict."""
        from laap.tools.session_search import TOOL_DEFINITIONS
        handler = TOOL_DEFINITIONS["search_sessions"]["handler"]
        result = handler({"query": "test", "limit": 1})
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert parsed["query"] == "test"

    def test_register_tools(self):
        """register_tools works with a mock registry."""
        from laap.tools.session_search import register_tools

        class MockRegistry:
            def __init__(self):
                self.tools = []
            def register(self, tool):
                self.tools.append(tool)

        # Test with actual registry if available
        try:
            from laap.tools.tool_registry import ToolRegistry
            reg = ToolRegistry()
            from laap.tools.session_search import register_tools
            register_tools(reg)
            assert len(reg._tools) >= 1
        except ImportError:
            pytest.skip("ToolRegistry not available")


class TestStreamingMarkdown:
    """Test StreamingMarkdown renderer."""

    def test_render_empty(self):
        from laap.ui.tui import rich_markdown
        result = rich_markdown("")
        assert result.plain == ""

    def test_render_plain_text(self):
        from laap.ui.tui import rich_markdown
        result = rich_markdown("Hello world")
        assert "Hello" in result.plain

    def test_render_bold(self):
        from laap.ui.tui import StreamingMarkdown
        result = StreamingMarkdown.render("Hello **world** here")
        assert "Hello" in result.plain
        assert "world" in result.plain
        assert "here" in result.plain

    def test_render_italic(self):
        from laap.ui.tui import StreamingMarkdown
        result = StreamingMarkdown.render("Hello *world*")
        assert "Hello world" in result.plain

    def test_render_code(self):
        from laap.ui.tui import StreamingMarkdown
        result = StreamingMarkdown.render("Use `print()` function")
        assert "print()" in result.plain

    def test_render_heading(self):
        from laap.ui.tui import StreamingMarkdown
        result = StreamingMarkdown.render("# Title")
        assert "Title" in result.plain

    def test_render_mixed(self):
        from laap.ui.tui import StreamingMarkdown
        text = "# Title\n\nSome **bold** and `code` here"
        result = StreamingMarkdown.render(text)
        assert "Title" in result.plain
        assert "bold" in result.plain
        assert "code" in result.plain

    def test_strip_markdown(self):
        from laap.ui.tui import StreamingMarkdown
        result = StreamingMarkdown.strip("**bold** and *italic* and `code`")
        assert "**" not in result
        assert "*" not in result
        assert "`" not in result
        assert result == "bold and italic and code"
