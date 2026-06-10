"""Built-in Skills — 内置技能集"""
from laap.agent_core.plugins.hooks import HookRegistry, HookPoint
import logging, json

logger = logging.getLogger("skills.builtin")

def register_all(registry):
    skills = [
        ("code_review", "Code review skill", code_review_init, code_review_handler),
        ("memory_helper", "Memory helper skill", mem_helper_init, mem_helper_handler),
        ("web_searcher", "Web search skill", web_search_init, web_search_handler),
        ("file_organizer", "File organizer skill", file_org_init, file_org_handler),
        ("data_analyzer", "Data analysis skill", data_ana_init, data_ana_handler),
    ]
    for name, desc, init_fn, handler_fn in skills:
        try:
            init_fn()
            registry.register(name, None, "builtin")
            logger.info(f"Builtin skill registered: {name}")
        except Exception as e:
            logger.error(f"Failed to register {name}: {e}")

def code_review_init():
    HookRegistry.register(HookPoint.AFTER_CHAT, lambda ctx: code_review_handler(ctx.data), "code_review")
def code_review_handler(data):
    if isinstance(data, str) and "def " in data:
        return f"Code review: found function definitions"
    return data

def mem_helper_init():
    HookRegistry.register(HookPoint.BEFORE_CHAT, lambda ctx: mem_helper_handler(ctx.data), "memory_helper")
def mem_helper_handler(data):
    return data

def web_search_init():
    pass
def web_search_handler(data):
    return data

def file_org_init():
    pass
def file_org_handler(data):
    return data

def data_ana_init():
    pass
def data_ana_handler(data):
    return data
