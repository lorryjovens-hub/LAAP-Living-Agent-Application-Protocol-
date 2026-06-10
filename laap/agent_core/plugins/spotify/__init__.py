"""Spotify Plugin — 音乐控制"""
import logging, json, base64
from laap.agent_core.plugins.hooks import HookRegistry, HookPoint
logger = logging.getLogger("plugins.spotify")

SPOTIFY_API = "https://api.spotify.com/v1"

def init_plugin(agent=None, config=None):
    logger.info("Spotify plugin initialized")
    return {"status": "ok"}

def search_track(query: str, token: str) -> dict:
    import urllib.request
    url = f"{SPOTIFY_API}/search?q={query}&type=track&limit=5"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())

def shutdown():
    pass
