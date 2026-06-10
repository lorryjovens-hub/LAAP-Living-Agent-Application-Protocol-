"""CredentialPool — 多Provider API Key管理"""
from __future__ import annotations
import json, os, logging, base64, time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("agent_core.credential_pool")

DEFAULT_PROVIDERS = {
    "deepseek": {"base": "https://api.deepseek.com/v1", "models": ["deepseek-chat", "deepseek-v4-flash", "deepseek-coder"]},
    "openai": {"base": "https://api.openai.com/v1", "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]},
    "anthropic": {"base": "https://api.anthropic.com/v1", "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]},
    "groq": {"base": "https://api.groq.com/openai/v1", "models": ["llama-3.3-70b", "mixtral-8x7b"]},
    "openrouter": {"base": "https://openrouter.ai/api/v1", "models": ["*"]},
}

class CredentialPool:
    """凭据池 — 管理多Provider API Key，自动轮换和故障转移"""
    
    def __init__(self):
        self._keys: Dict[str, List[Dict]] = {}
        self._current_index: Dict[str, int] = {}
        self._quotas: Dict[str, Dict] = {}
        self._config_path = os.path.expanduser("~/.laap/credentials.json")
        self._load()
    
    def _load(self):
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r') as f:
                    data = json.load(f)
                for provider, keys in data.items():
                    if isinstance(keys, list):
                        self._keys[provider] = keys
                    elif isinstance(keys, str):
                        self._keys[provider] = [{"key": keys}]
                    self._current_index[provider] = 0
            except: pass
    
    def save(self):
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        with open(self._config_path, 'w') as f:
            json.dump({p: [k.get("key", "") for k in keys] for p, keys in self._keys.items()}, f, indent=2)
    
    def add_key(self, provider: str, api_key: str, model: str = "", quota: int = 0):
        if provider not in self._keys:
            self._keys[provider] = []
            self._current_index[provider] = 0
        entry = {"key": api_key, "model": model, "added": time.time()}
        if quota:
            entry["quota"] = quota
            entry["used"] = 0
        self._keys[provider].append(entry)
        self.save()
    
    def get_key(self, provider: str) -> Optional[str]:
        """获取下一个可用的API Key (轮换)"""
        keys = self._keys.get(provider, [])
        if not keys:
            return None
        idx = self._current_index.get(provider, 0)
        # 检查配额
        for _ in range(len(keys)):
            entry = keys[idx]
            if "quota" in entry and entry.get("used", 0) >= entry["quota"]:
                idx = (idx + 1) % len(keys)
                continue
            self._current_index[provider] = (idx + 1) % len(keys)
            entry["used"] = entry.get("used", 0) + 1
            return entry["key"]
        return None
    
    def get_base_url(self, provider: str) -> str:
        return DEFAULT_PROVIDERS.get(provider, {}).get("base", "")
    
    def get_models(self, provider: str) -> List[str]:
        return DEFAULT_PROVIDERS.get(provider, {}).get("models", [])
    
    def list_providers(self) -> List[str]:
        return list(self._keys.keys())
    
    def get_stats(self) -> dict:
        return {
            "providers": len(self._keys),
            "total_keys": sum(len(v) for v in self._keys.values()),
            "providers_list": list(self._keys.keys()),
        }
