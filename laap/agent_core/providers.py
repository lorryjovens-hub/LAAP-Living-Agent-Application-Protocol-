"""Providers — 能力提供者注册中心(搜索/浏览器/TTS/STT/图像/视频)"""
from __future__ import annotations
import time, json, logging, abc
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("agent_core.providers")

class BaseProvider(abc.ABC):
    name: str = ""
    async def execute(self, **kwargs) -> Any: ...
    def get_stats(self) -> dict: return {}

class WebSearchProvider(BaseProvider):
    name = "web_search"
    async def execute(self, query: str, limit: int = 5) -> str:
        return f"[WebSearch] {query} - {limit} results"

class BrowserProvider(BaseProvider):
    name = "browser"
    async def execute(self, action: str, url: str = "", **kwargs) -> str:
        return f"[Browser] {action} {url}"

class TTSProvider(BaseProvider):
    name = "tts"
    async def execute(self, text: str, voice: str = "default") -> bytes:
        return b""

class STTProvider(BaseProvider):
    name = "stt"
    async def execute(self, audio: bytes, language: str = "zh") -> str:
        return "[Transcription]"

class ImageGenProvider(BaseProvider):
    name = "image_gen"
    async def execute(self, prompt: str, size: str = "1024x1024") -> str:
        return f"[Image] {prompt[:30]}..."

class VideoGenProvider(BaseProvider):
    name = "video_gen"
    async def execute(self, prompt: str, duration: int = 5) -> str:
        return f"[Video] {prompt[:30]}..."

class ProviderRegistry:
    """统一注册中心"""
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
    def register(self, provider: BaseProvider):
        self._providers[provider.name] = provider
    def get(self, name: str) -> Optional[BaseProvider]:
        return self._providers.get(name)
    def list(self) -> List[str]:
        return list(self._providers.keys())
    def init_defaults(self):
        for p in [WebSearchProvider(), BrowserProvider(), TTSProvider(), STTProvider(), ImageGenProvider(), VideoGenProvider()]:
            self.register(p)
