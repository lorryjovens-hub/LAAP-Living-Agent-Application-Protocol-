"""Security Plugin — 内容安全过滤"""
from laap.agent_core.plugins.hooks import HookRegistry, HookPoint
import re

BLOCKED_PATTERNS = [
    r"(?i)(rm\s+-rf|format\s+[a-z]:|del\s+/[fsq])",
    r"(?i)(DROP\s+TABLE|DELETE\s+FROM)",
]

def init_plugin(agent=None, config=None):
    HookRegistry.register(HookPoint.BEFORE_CHAT, check_input, "security")
    HookRegistry.register(HookPoint.BEFORE_TOOL, check_tool_call, "security")
    return {"status": "ok"}

def check_input(ctx):
    text = ctx.data if isinstance(ctx.data, str) else ""
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text):
            ctx.stop_propagation = True
            return "⚠️ 内容被安全策略阻止: 检测到危险命令模式"
    return ctx.data

def check_tool_call(ctx):
    text = str(ctx.data)
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text):
            ctx.stop_propagation = True
            return json.dumps({"error": "安全策略阻止", "pattern": pattern})

def shutdown():
    HookRegistry.unregister(HookPoint.BEFORE_CHAT, check_input)
    HookRegistry.unregister(HookPoint.BEFORE_TOOL, check_tool_call)

import json
