"""
LAAP Agent 内置工具 — 类似 Hermes 的常用工具集
"""
from __future__ import annotations
import time, json, os, sys, logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("agent_core.tools.builtin")

class BuiltinTools:
    """内置工具注册器"""
    
    @staticmethod
    def register_all(tool_manager):
        """注册所有内置工具 (50+)"""
        from laap.agent_core.tool_manager import Tool
        tm = tool_manager
        # 基础工具
        base_tools = [
            Tool("read_file", "读取文件内容", {"type":"object","properties":{"path":{"type":"string"},"offset":{"type":"integer"},"limit":{"type":"integer"}},"required":["path"]}, category="file"),
            Tool("write_file", "写入文件内容", {"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}, category="file"),
            Tool("list_files", "列出目录文件", {"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}, category="file"),
            Tool("get_time", "获取当前时间", {"type":"object","properties":{}}, category="system"),
            Tool("think", "内部思考和分析", {"type":"object","properties":{"thought":{"type":"string"}},"required":["thought"]}, category="system"),
            Tool("finish", "完成任务返回最终结果", {"type":"object","properties":{"result":{"type":"string"},"summary":{"type":"string"}},"required":["result"]}, category="system"),
        ]
        for t in base_tools:
            tm.register(t)
        
        # 从各个工具模块加载
        try:
            from laap.agent_core.tools import web_tools, code_tools, file_tools, media_tools, data_tools, system_tools, computer_use_tool, browser_tool, vision_tool, terminal_tool
            for mod in [web_tools, code_tools, file_tools, media_tools, data_tools, system_tools, computer_use_tool, browser_tool, vision_tool, terminal_tool]:
                if hasattr(mod, "TOOL_DEFS"):
                    for td in mod.TOOL_DEFS:
                        params = {"type":"object","properties":td.get("params",{}),"required":td.get("req",[])}
                        cat = mod.__name__.split(".")[-1].replace("_tools","")
                        tm.register(Tool(td["name"], td.get("desc",""), params, category=cat))
        except Exception as e:
            import logging
            logging.getLogger("builtin").error(f"Tool load error: {e}")
        
        # 返回总数
        return tm.list_tools()


# 工具实现
def _read_file(path, offset=1, limit=500):
    """读取文件"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        selected = lines[offset-1:offset-1+limit]
        return "".join(selected)
    except Exception as e:
        return f"Error: {e}"

def _write_file(path, content):
    """写入文件"""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Written {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"

def _list_files(path="."):
    """列出文件"""
    try:
        files = os.listdir(path)
        return "\n".join(sorted(files))
    except Exception as e:
        return f"Error: {e}"

def _get_time():
    """获取当前时间"""
    return time.strftime("%Y-%m-%d %H:%M:%S")

def _think(thought):
    """内部思考"""
    logger.info(f"Agent thinking: {thought[:100]}")
    return f"思考记录: {thought[:200]}"

def _finish(result, summary=""):
    """完成"""
    return f"✅ {summary}\n结果: {result}"

# Map function names to implementations
_IMPLS = {
    "read_file": _read_file,
    "write_file": _write_file,
    "list_files": _list_files,
    "get_time": _get_time,
    "think": _think,
    "finish": _finish,
}

# 加载新工具模块的实现
def _load_tool_impls():
    try:
        from laap.agent_core.tools import web_tools, code_tools, file_tools, media_tools, data_tools, system_tools, computer_use_tool, browser_tool, vision_tool, terminal_tool
        for mod in [web_tools, code_tools, file_tools, media_tools, data_tools, system_tools, computer_use_tool, browser_tool, vision_tool, terminal_tool]:
            if hasattr(mod, "TOOL_DEFS"):
                for td in mod.TOOL_DEFS:
                    _IMPLS[td["name"]] = td["fn"]
    except Exception as e:
        import logging
        logging.getLogger("builtin").error(f"Impl load error: {e}")

_load_tool_impls()

def register_all_implementations(tool_manager):
    """注册所有工具实现"""
    count = 0
    for name, impl in _IMPLS.items():
        tool = tool_manager.get(name)
        if tool:
            tool.handler = impl
            count += 1
    logger.info(f"Implementations set for {count} tools")
