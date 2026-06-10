"""Context Engine Plugin — 上下文压缩与管理"""
from laap.agent_core.plugins.hooks import HookRegistry, HookPoint

def init_plugin(agent=None, config=None):
    HookRegistry.register(HookPoint.AFTER_CHAT, after_chat, "context_engine")
    return {"status": "ok"}

def after_chat(ctx):
    if ctx.data and len(ctx.data) > 2000:
        ctx.result = ctx.data[:1500] + "...[已压缩]"
    return ctx.result

def shutdown():
    HookRegistry.unregister(HookPoint.AFTER_CHAT, after_chat)
