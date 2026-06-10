"""Image Generation Plugin"""
import logging
from laap.agent_core.plugins.hooks import HookRegistry, HookPoint
logger = logging.getLogger("plugins.image_gen")

def init_plugin(agent=None, config=None):
    logger.info("Image generation plugin initialized")
    return {"status": "ok"}

def generate(prompt: str, api_key: str = "") -> str:
    import json, urllib.request
    try:
        url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        data = json.dumps({"text_prompts": [{"text": prompt}], "cfg_scale": 7, "steps": 30}).encode()
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            return f"Generated image from prompt: {prompt[:50]}"
    except Exception as e:
        return f"Image gen error: {e}"

def shutdown():
    pass
