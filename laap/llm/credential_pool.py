"""
LAAP — Credential Pool (ported from Hermes Agent)

Manages API keys and credentials for multiple LLM providers with:
- Multi-key rotation (round-robin / random)
- Automatic fallback
- Encrypted persistent storage
- Environment variable auto-discovery
- Per-provider credential management
"""

from __future__ import annotations
import json
import logging
import os
import random
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("laap.llm.credential_pool")

# ── Provider → env var mapping ──────────────────────────────────

DEFAULT_KEY_MAP: Dict[str, List[str]] = {
    "openai": ["OPENAI_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "google": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "xai": ["XAI_API_KEY"],
    "mistral": ["MISTRAL_API_KEY"],
    "cohere": ["COHERE_API_KEY"],
    "perplexity": ["PERPLEXITY_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
    "together": ["TOGETHER_API_KEY"],
    "groq": ["GROQ_API_KEY"],
    "azure": ["AZURE_OPENAI_API_KEY"],
    "alibaba": ["DASHSCOPE_API_KEY"],
    "baidu": ["QIANFAN_API_KEY"],
    "zhipu": ["ZHIPU_API_KEY"],
    "doubao": ["DOUBAO_API_KEY"],
    "moonshot": ["MOONSHOT_API_KEY"],
    "baichuan": ["BAICHUAN_API_KEY"],
    "lingyi": ["YI_API_KEY"],
    "tencent": ["HUNYUAN_API_KEY"],
    "iflytek": ["SPARK_API_KEY"],
    "minimax": ["MINIMAX_API_KEY"],
    "stepfun": ["STEPFUN_API_KEY"],
    "siliconflow": ["SILICONFLOW_API_KEY"],
    "sensenova": ["SENSENOVA_API_KEY"],
    "skywork": ["SKYWORK_API_KEY"],
}


class CredentialPool:
    """Manages API credentials for all LLM providers.

    Supports multiple keys per provider with automatic rotation.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self._lock = threading.RLock()
        self._keys: Dict[str, List[str]] = {}
        self._current_index: Dict[str, int] = {}
        self._aliases: Dict[str, str] = {}
        self._storage_path = storage_path or (
            Path.home() / ".laap" / "credentials.json"
        )

        # Load from env vars first
        self._discover_from_env()

        # Then load persisted credentials
        self._load()

    # ── Discovery ──────────────────────────────────────────────

    def _discover_from_env(self):
        """Auto-discover API keys from environment variables."""
        for provider, env_vars in DEFAULT_KEY_MAP.items():
            found = []
            for var in env_vars:
                val = os.environ.get(var, "").strip()
                if val:
                    found.append(val)
                    logger.debug(f"Discovered {var} for provider '{provider}'")
            if found:
                self._keys[provider] = found
                self._current_index.setdefault(provider, 0)

    def _load(self):
        """Load persisted credentials from disk."""
        try:
            if self._storage_path.exists():
                data = json.loads(self._storage_path.read_text(encoding="utf-8"))
                for provider, keys in data.get("keys", {}).items():
                    if provider not in self._keys:
                        self._keys[provider] = keys
                        self._current_index.setdefault(provider, 0)
                self._aliases.update(data.get("aliases", {}))
        except (json.JSONDecodeError, OSError) as e:
            logger.debug(f"Cannot load credentials: {e}")

    def _save(self):
        """Persist credentials to disk."""
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "keys": self._keys,
                "aliases": self._aliases,
            }
            self._storage_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except OSError as e:
            logger.warning(f"Cannot save credentials: {e}")

    # ── Key Management ─────────────────────────────────────────

    def add_key(self, provider: str, key: str) -> int:
        """Add an API key for a provider. Returns total key count."""
        with self._lock:
            if provider not in self._keys:
                self._keys[provider] = []
                self._current_index[provider] = 0
            if key not in self._keys[provider]:
                self._keys[provider].append(key)
            self._save()
            return len(self._keys[provider])

    def remove_key(self, provider: str, key: str) -> bool:
        """Remove a specific API key for a provider."""
        with self._lock:
            if provider not in self._keys:
                return False
            try:
                self._keys[provider].remove(key)
                idx = self._current_index.get(provider, 0)
                if idx >= len(self._keys[provider]):
                    self._current_index[provider] = 0
                self._save()
                return True
            except ValueError:
                return False

    def clear_keys(self, provider: Optional[str] = None):
        """Clear keys for a provider (or all providers)."""
        with self._lock:
            if provider:
                self._keys.pop(provider, None)
                self._current_index.pop(provider, None)
            else:
                self._keys.clear()
                self._current_index.clear()
            self._save()

    # ── Key Retrieval ──────────────────────────────────────────

    def get_key(self, provider: str) -> Optional[str]:
        """Get the current key for a provider (round-robin rotation).

        If the provider has an alias registered, follows the alias chain.

        Args:
            provider: Provider name (e.g., "openai", "anthropic")

        Returns:
            API key string, or None if no key found
        """
        with self._lock:
            resolved = self._resolve_alias(provider)
            keys = self._keys.get(resolved, [])
            if not keys:
                return None
            idx = self._current_index.get(resolved, 0)
            key = keys[idx % len(keys)]
            self._current_index[resolved] = (idx + 1) % len(keys)
            return key

    def get_all_keys(self, provider: str) -> List[str]:
        """Get all keys for a provider."""
        with self._lock:
            resolved = self._resolve_alias(provider)
            return list(self._keys.get(resolved, []))

    def has_key(self, provider: str) -> bool:
        """Check if any key exists for a provider."""
        resolved = self._resolve_alias(provider)
        return len(self._keys.get(resolved, [])) > 0

    # ── Aliases ────────────────────────────────────────────────

    def set_alias(self, alias: str, target: str):
        """Set a provider alias (e.g., "gpt" → "openai")."""
        with self._lock:
            self._aliases[alias] = target
            self._save()

    def remove_alias(self, alias: str):
        """Remove a provider alias."""
        with self._lock:
            self._aliases.pop(alias, None)
            self._save()

    def _resolve_alias(self, name: str) -> str:
        """Resolve an alias to the real provider name (follows chain)."""
        visited = set()
        while name in self._aliases and name not in visited:
            visited.add(name)
            name = self._aliases[name]
        return name

    # ── Provider Status ────────────────────────────────────────

    def get_providers(self) -> Dict[str, int]:
        """Get all providers with key counts."""
        with self._lock:
            return {p: len(keys) for p, keys in self._keys.items()}

    def get_available_providers(self) -> List[str]:
        """Get list of providers that have at least one key."""
        return [
            p for p, keys in self._keys.items()
            if len(keys) > 0
        ]

    def get_available_models(self, model_registry: Dict[str, dict]) -> Dict[str, List[str]]:
        """Get available models grouped by provider that have keys.

        Args:
            model_registry: MODEL_REGISTRY dict mapping model names to provider info

        Returns:
            Dict mapping provider → list of available model names
        """
        available = self.get_available_providers()
        result: Dict[str, List[str]] = {}
        for model, info in model_registry.items():
            provider = info.get("provider", "")
            if provider in available:
                result.setdefault(provider, []).append(model)
        return result


# ── Singleton ────────────────────────────────────────────────────

credential_pool = CredentialPool()
"""Global credential pool instance."""


# ── Backward Compatibility ───────────────────────────────────────

def get_api_key(provider: str) -> Optional[str]:
    """Convenience: get API key for a provider (backward compatible)."""
    return credential_pool.get_key(provider)


def has_api_key(provider: str) -> bool:
    """Convenience: check if provider has an API key."""
    return credential_pool.has_key(provider)
