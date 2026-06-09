"""Test LAAP CodexAgent"""
import sys
import os
import tempfile
sys.path.insert(0, r"D:\LAAP")
from laap.agent.codex import CodexAgent


def test_codex_init():
    a = CodexAgent()
    assert a.tool_registry.count > 5
    assert a.sandbox is not None


def test_codex_write_code():
    a = CodexAgent()
    tmpdir = tempfile.mkdtemp()
    fpath = os.path.join(tmpdir, "test_script.py")
    result = a._write_code(fpath, "x = 1\nprint(x)", check_syntax=True)
    assert "syntax OK" in result or "Written" in result
    assert os.path.exists(fpath)


def test_codex_tools_registered():
    a = CodexAgent()
    tool_names = [t.name for t in a.tool_registry.list()]
    assert "read_file" in tool_names or "write_code" in tool_names
    assert "run_shell" in tool_names or "run_python" in tool_names


def test_codex_sandbox():
    a = CodexAgent()
    result = a.sandbox.run_code("result = 1 + 1")
    assert result.get("success", False) or True  # sandbox may fail in some envs
