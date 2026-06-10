"""Web Plugin — 网页抓取与渲染"""
import logging, json, urllib.request, re
from laap.agent_core.plugins.hooks import HookRegistry, HookPoint
logger = logging.getLogger("plugins.web")

def init_plugin(agent=None, config=None):
    HookRegistry.register(HookPoint.AFTER_CHAT, web_handler, "web")
    return {"status": "ok", "features": ["fetch", "render"]}

def web_handler(ctx):
    text = str(ctx.data) if ctx.data else ""
    if "http://" in text or "https://" in text:
        urls = re.findall(r'https?://[^\s]+', text)
        for url in urls[:3]:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "LAAP/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html = resp.read().decode('utf-8', errors='replace')[:1000]
                ctx.result = f"[Fetched {url}] {re.sub(r'<[^>]+>', ' ', html)[:200]}"
            except Exception as e:
                ctx.result = f"[Fetch Error] {e}"
    return ctx.result

def shutdown():
    HookRegistry.unregister(HookPoint.AFTER_CHAT, web_handler)
