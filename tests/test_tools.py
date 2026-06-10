"""Tool system tests — 25+ test functions covering registry, calls, built-in, web, file, system tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Dict, Any, List


class TestToolManagerRegistry:
    """Tool registry tests."""

    def test_manager_create(self):
        from laap.agent_core.tool_manager import ToolManager
        tm = ToolManager()
        assert tm.registry == {}

    def test_register_tool(self):
        from laap.agent_core.tool_manager import ToolManager
        tm = ToolManager()
        tool_fn = MagicMock()
        tm.register_tool("test_tool", tool_fn, "A test tool")
        assert "test_tool" in tm.registry

    def test_register_tool_with_params(self):
        from laap.agent_core.tool_manager import ToolManager
        tm = ToolManager()
        tool_fn = MagicMock()
        params = {"type": "object", "properties": {"x": {"type": "string"}}}
        tm.register_tool("test_tool", tool_fn, "desc", params)
        assert tm.registry["test_tool"]["parameters"] == params

    def test_unregister_tool(self):
        from laap.agent_core.tool_manager import ToolManager
        tm = ToolManager()
        tm.register_tool("t", MagicMock(), "d")
        tm.unregister_tool("t")
        assert "t" not in tm.registry

    def test_list_tools(self):
        from laap.agent_core.tool_manager import ToolManager
        tm = ToolManager()
        tm.register_tool("a", MagicMock(), "desc a")
        tm.register_tool("b", MagicMock(), "desc b")
        names = tm.list_tools()
        assert "a" in names
        assert "b" in names

    def test_duplicate_registration(self):
        from laap.agent_core.tool_manager import ToolManager
        tm = ToolManager()
        tm.register_tool("t", MagicMock(), "d")
        with pytest.raises(ValueError):
            tm.register_tool("t", MagicMock(), "d")


class TestToolManagerCall:
    """Tool execution tests."""

    def test_execute_tool_success(self):
        from laap.agent_core.tool_manager import ToolManager
        tm = ToolManager()
        inner = MagicMock(return_value="done")
        tm.register_tool("greet", inner, "Say hello")
        result = tm.execute_tool("greet", {"name": "World"})
        assert result == "done"

    def test_execute_tool_unknown(self):
        from laap.agent_core.tool_manager import ToolManager
        tm = ToolManager()
        with pytest.raises(KeyError):
            tm.execute_tool("nonexistent", {})

    def test_execute_tool_with_default_args(self):
        from laap.agent_core.tool_manager import ToolManager
        tm = ToolManager()
        def fn(x="default"):
            return f"got {x}"
        tm.register_tool("test", fn, "d")
        result = tm.execute_tool("test", {})
        assert result == "got default"

    def test_execute_tool_error_handling(self):
        from laap.agent_core.tool_manager import ToolManager
        tm = ToolManager()
        def failing():
            raise RuntimeError("fail")
        tm.register_tool("fail", failing, "d")
        with pytest.raises(RuntimeError):
            tm.execute_tool("fail", {})


class TestBuiltinTools:
    """Built-in tool tests."""

    def test_read_file_tool(self):
        from laap.agent_core.tools.file_tools import read_file
        tool = read_file
        assert tool is not None

    def test_write_file_tool(self):
        from laap.agent_core.tools.file_tools import write_file
        assert callable(write_file)

    def test_execute_command_tool(self):
        from laap.agent_core.tools.system_tools import execute_command
        assert callable(execute_command)

    def test_search_files_tool(self):
        from laap.agent_core.tools.file_tools import search_files
        assert callable(search_files)

    def test_builtin_tool_list(self):
        from laap.agent_core.tools.builtin import get_builtin_tools
        tools = get_builtin_tools()
        assert isinstance(tools, dict)
        assert len(tools) > 0

    def test_code_edit_tool(self):
        from laap.agent_core.tools.code_tools import edit_code
        assert callable(edit_code)


class TestWebTools:
    """Web tool tests."""

    def test_http_get_tool(self):
        from laap.agent_core.tools.browser_tool import http_get
        assert callable(http_get)

    def test_fetch_url_tool(self):
        from laap.agent_core.tools.browser_tool import fetch_url
        assert callable(fetch_url)

    def test_search_web_tool(self):
        from laap.agent_core.tools.media_tools import search_web
        assert callable(search_web)


class TestFileTools:
    """File tool tests."""

    def test_list_directory(self):
        from laap.agent_core.tools.file_tools import list_directory
        assert callable(list_directory)

    def test_copy_file(self):
        from laap.agent_core.tools.file_tools import copy_file
        assert callable(copy_file)

    def test_move_file(self):
        from laap.agent_core.tools.file_tools import move_file
        assert callable(move_file)

    def test_delete_file(self):
        from laap.agent_core.tools.file_tools import delete_file
        assert callable(delete_file)

    def test_make_directory(self):
        from laap.agent_core.tools.file_tools import make_directory
        assert callable(make_directory)

    def test_path_safety_check(self):
        from laap.tools.path_security import is_path_safe
        assert callable(is_path_safe)


class TestSystemTools:
    """System tool tests."""

    def test_get_system_info(self):
        from laap.agent_core.tools.system_tools import get_system_info
        assert callable(get_system_info)

    def test_get_process_list(self):
        from laap.agent_core.tools.system_tools import get_process_list
        assert callable(get_process_list)

    def test_get_disk_usage(self):
        from laap.agent_core.tools.system_tools import get_disk_usage
        assert callable(get_disk_usage)
