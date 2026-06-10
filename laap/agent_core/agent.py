"""LAAP Agent — 全系统集成核心"""
from __future__ import annotations
import time, json, logging, uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from laap.agent_core.context import Context, Role
from laap.agent_core.llm_provider import LLMFactory
from laap.agent_core.tool_manager import ToolManager, Tool
from laap.agent_core.planner import Planner
from laap.agent_core.executor import Executor
from laap.agent_core.memory_bridge import MemoryBridge
from laap.agent_core.context_compressor import ContextCompressor
from laap.agent_core.cron import CronScheduler
from laap.agent_core.background_review import BackgroundReviewer
from laap.agent_core.llm_adapters import AdapterRegistry
from laap.agent_core.tools.builtin import BuiltinTools, register_all_implementations
from laap.agent_core.plugins.hooks import HookRegistry, HookPoint
from laap.agent_core.platforms.manager import PlatformManager
from laap.agent_core.plugins.manager import PluginManager as _PluginManager

logger = logging.getLogger("agent_core.agent")

class AgentState(str, Enum):
    IDLE="idle"; THINKING="thinking"; ACTING="acting"; OBSERVING="observing"; DONE="done"

@dataclass
class AgentConfig:
    name: str="LAAP-Agent"; version: str="1.0.0"
    system_prompt: str=""; max_iterations: int=20; max_tokens: int=128000
    temperature: float=0.7; llm_provider: str="deepseek"; llm_model: str="deepseek-v4-flash"
    enable_memory: bool=True; enable_tools: bool=True; enable_planning: bool=True

DEFAULT_SYSTEM = "你是LAAP智能体。有记忆、有工具、可规划。请用中文回答。"

class Agent:
    def __init__(self, config=None):
        self.config = config or AgentConfig()
        self.state = AgentState.IDLE
        self.context = Context(max_tokens=self.config.max_tokens)
        self.tool_mgr = ToolManager()
        self.planner = Planner()
        self.executor = Executor(self.tool_mgr)
        self.memory = MemoryBridge() if self.config.enable_memory else None
        self.compressor = ContextCompressor()
        self.cron = CronScheduler()
        self.reviewer = BackgroundReviewer()
        self.adapter_registry = AdapterRegistry()
        self.platform_mgr = PlatformManager(handler=self._platform_handler)
        self.plugin_mgr = None
        
        self.llm = LLMFactory.create(self.config.llm_provider, self.config.llm_model, temperature=self.config.temperature)
        self.context.set_system(self.config.system_prompt or DEFAULT_SYSTEM)
        self._session_id = "sess_" + uuid.uuid4().hex[:8]
        self._stats = {"total_turns": 0, "total_tool_calls": 0}
        
        BuiltinTools.register_all(self.tool_mgr)
        register_all_implementations(self.tool_mgr)
        self._add_memory_tools()
        self.cron.start()
        logger.info(f"Agent ready: {self.config.name}")
    
    def _add_memory_tools(self):
        if not self.memory: return
        self.tool_mgr.register(Tool("remember","记住信息",{"type":"object","properties":{"fact":{"type":"string"},"importance":{"type":"number"}},"required":["fact"]},handler=lambda fact,imp=0.5:self.memory.remember_fact(fact,imp),category="memory"))
        self.tool_mgr.register(Tool("recall","回忆信息",{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]},handler=lambda q:json.dumps(self.memory.search_memory(q),ensure_ascii=False),category="memory"))
    
    def _platform_handler(self, event):
        HookRegistry.trigger(HookPoint.BEFORE_CHAT, event.text)
        resp = self.chat(event.text)
        HookRegistry.trigger(HookPoint.AFTER_CHAT, resp)
        return resp
    
    def init_plugins(self):
        if self.plugin_mgr is None:
            self.plugin_mgr = _PluginManager()
            self.plugin_mgr.init_plugins(agent=self)
        return self.plugin_mgr
    
    def chat(self, message):
        self._stats["total_turns"] += 1
        self.state = AgentState.THINKING
        self.context.add(Role.USER, message)
        if self.context.total_tokens() > self.config.max_tokens * 0.8:
            self.context.messages = self.compressor.compress(self.context.get_messages())
        for _ in range(self.config.max_iterations):
            resp = self.llm.chat(self.context.get_messages(), self.tool_mgr.get_openai_tools() if self.config.enable_tools else [])
            if not resp.content and resp.finish_reason == "tool_calls":
                self.state = AgentState.ACTING
                result = self._exec_tool(message)
                self._stats["total_tool_calls"] += 1
                self.state = AgentState.OBSERVING
                obs = result.output or str(result.data or "")
                self.context.add(Role.TOOL, obs, tool_call_id="c1", name="tool")
            elif resp.finish_reason == "error":
                self.context.add(Role.ASSISTANT, resp.content)
                self.state = AgentState.DONE
                return resp.content
            else:
                self.context.add(Role.ASSISTANT, resp.content)
                self.state = AgentState.DONE
                if self.memory:
                    self.memory.remember_interaction(message, resp.content)
                return resp.content
        self.state = AgentState.DONE
        return "(已达上限)"
    
    def stream_chat(self, message):
        self.context.add(Role.USER, message)
        yield ("status", "thinking")
        full = ""
        try:
            for token in self.llm.stream_chat(self.context.get_messages()):
                full += token
                yield ("token", token)
            self.context.add(Role.ASSISTANT, full)
            if self.memory:
                self.memory.remember_interaction(message, full)
            yield ("done", full)
        except Exception as e:
            yield ("error", str(e))
    
    def _exec_tool(self, msg):
        m = msg.lower()
        for kws, name, args in [
            (["时间","几点了","time"],"get_time",{}),
            (["搜索","search"],"web_search",{"query":msg}),
            (["读","read","文件"],"read_file",{"path":".","limit":50}),
            (["记忆","记住","remember"],"remember",{"fact":msg}),
            (["回忆","recall"],"recall",{"query":msg}),
            (["截图","screenshot"],"screenshot",{}),
            (["系统","info"],"system_info",{}),
        ]:
            if any(k in m for k in kws):
                return self.tool_mgr.call(name, args)
        return self.tool_mgr.call("think", {"thought": "Process: " + msg[:100]})
    
    def get_stats(self):
        return dict(self._stats, state=self.state.value, context_tokens=self.context.total_tokens(),
                    tools=len(self.tool_mgr.list_tools()), memory=self.memory.get_stats() if self.memory else {})
    
    def to_dict(self):
        return {"name":self.config.name,"state":self.state.value,"stats":self.get_stats(),
                "platforms":self.platform_mgr.get_stats()}
    
    def reset(self):
        self.context.clear()
        self.state = AgentState.IDLE
