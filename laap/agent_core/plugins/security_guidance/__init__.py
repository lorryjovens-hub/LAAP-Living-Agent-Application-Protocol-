"""Security Guidance Plugin"""
import logging, re
from laap.agent_core.plugins.hooks import HookRegistry, HookPoint
logger = logging.getLogger("plugins.security_guidance")

PATTERNS = [
    ("rm -rf /", "rm -rf / will delete sys"),
    ("DROP TABLE", "DROP TABLE deletes database"),
    ("password=", "Hardcoded password?"),
]

def init_plugin(agent=None, config=None):
    HookRegistry.register(HookPoint.BEFORE_TOOL, security_check, "security_guidance")
    return {"status": "ok"}

def security_check(ctx):
    text = str(ctx.data)
    for pattern, warning in PATTERNS:
        if pattern.lower() in text.lower():
            ctx.result = warning
            ctx.stop_propagation = True
            return warning
    return ctx.data

def shutdown():
    HookRegistry.unregister(HookPoint.BEFORE_TOOL, security_check)
