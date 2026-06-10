"""Teams Pipeline Plugin"""
import logging, json, time
from laap.agent_core.plugins.hooks import HookRegistry, HookPoint
logger = logging.getLogger("plugins.teams_pipeline")

_pipeline = []

def init_plugin(agent=None, config=None):
    HookRegistry.register(HookPoint.AFTER_CHAT, pipeline_handler, "teams_pipeline")
    return {"status": "ok"}

def pipeline_handler(ctx):
    _pipeline.append({"time": time.time(), "data": str(ctx.data)[:100]})
    if len(_pipeline) > 100:
        _pipeline.pop(0)
    return ctx.data

def get_pipeline():
    return list(_pipeline)

def shutdown():
    HookRegistry.unregister(HookPoint.AFTER_CHAT, pipeline_handler)
