"""LLM Adapters — Anthropic / Gemini / Bedrock 适配器"""
from __future__ import annotations
import json, logging, time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent_core.llm_adapters")

class AnthropicAdapter:
    def __init__(self, api_key: str = "", model: str = "claude-3-sonnet"):
        self.api_key = api_key
        self.model = model
        self.api_base = "https://api.anthropic.com/v1"
    
    def chat(self, messages: List[dict]) -> str:
        """Call Anthropic API"""
        try:
            import urllib.request
            headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01",
                      "Content-Type": "application/json"}
            body = json.dumps({"model": self.model, "messages": messages,
                             "max_tokens": 4096}).encode()
            req = urllib.request.Request(f"{self.api_base}/messages", data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            return data.get("content", [{}])[0].get("text", "")
        except Exception as e:
            return f"[Anthropic Error] {e}"

class GeminiAdapter:
    def __init__(self, api_key: str = "", model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
    
    def chat(self, messages: List[dict]) -> str:
        """Call Gemini API"""
        try:
            import urllib.request
            # Convert OpenAI format to Gemini format
            contents = []
            for msg in messages:
                role = "user" if msg["role"] in ("user", "tool") else "model"
                contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            body = json.dumps({"contents": contents}).encode()
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        except Exception as e:
            return f"[Gemini Error] {e}"

class AdapterRegistry:
    def __init__(self):
        self._adapters = {}
    
    def register(self, name: str, adapter):
        self._adapters[name] = adapter
    
    def get(self, name: str):
        return self._adapters.get(name)
    
    def chat(self, name: str, messages: List[dict]) -> str:
        adapter = self.get(name)
        if adapter:
            return adapter.chat(messages)
        return f"No adapter: {name}"
