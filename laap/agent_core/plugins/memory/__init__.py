"""Memory Plugin — 自动记忆持久化"""
from laap.agent_core.plugins.hooks import HookRegistry, HookPoint
import json, os, time

_store_path = os.path.expanduser("~/.laap/plugin_memory.json")

def init_plugin(agent=None, config=None):
    HookRegistry.register(HookPoint.BEFORE_CHAT, load_memory, "memory")
    HookRegistry.register(HookPoint.AFTER_CHAT, save_memory, "memory")
    return {"status": "ok", "agent": agent.config.name if agent else "none"}

def load_memory(ctx):
    if os.path.exists(_store_path):
        try:
            with open(_store_path, 'r') as f:
                ctx.data = json.load(f)
        except: pass
    return ctx.data

def save_memory(ctx):
    try:
        with open(_store_path, 'w') as f:
            json.dump({"last_update": time.time(), "data": str(ctx.data)[:100]}, f)
    except: pass
    return ctx.data

def shutdown():
    HookRegistry.unregister(HookPoint.BEFORE_CHAT, load_memory)
    HookRegistry.unregister(HookPoint.AFTER_CHAT, save_memory)
