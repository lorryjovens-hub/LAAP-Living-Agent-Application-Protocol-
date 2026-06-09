"""
LAAP — Model Discovery Engine

Auto-discover latest model IDs from LLM provider APIs.
Fetches /v1/models endpoints, validates connectivity,
and auto-updates the model registry with the latest models.
"""
from __future__ import annotations
import json, logging, os, time, threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

logger = logging.getLogger("laap.llm.discovery")


@dataclass
class DiscoveredModel:
    """A model discovered from a provider API"""
    id: str
    provider: str
    owned_by: str = ""
    created: int = 0
    object_type: str = "model"
    aliases: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    discovered_at: float = field(default_factory=time.time)
    verified: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider": self.provider,
            "owned_by": self.owned_by,
            "verified": self.verified,
        }


@dataclass
class DiscoveryResult:
    """Result of a model discovery scan"""
    provider: str
    total_found: int
    models: List[DiscoveredModel]
    new_models: List[str]          # Model IDs not in current registry
    errors: List[str]
    duration_ms: float
    timestamp: float = field(default_factory=time.time)


class ModelDiscovery:
    """Discover latest model IDs from provider APIs

    Supports:
      - OpenAI-compatible /v1/models endpoints
      - Direct API connectivity validation
      - Registry diff (what's new vs what we have)
      - Auto-suggest model ID updates
    """

    # Providers known to support /v1/models endpoint
    MODELS_ENDPOINT_PROVIDERS = {
        "openai":       "https://api.openai.com/v1/models",
        "deepseek":     "https://api.deepseek.com/v1/models",
        "xai":          "https://api.x.ai/v1/models",
        "mistral":      "https://api.mistral.ai/v1/models",
        "cohere":       "https://api.cohere.ai/v1/models",
        "perplexity":   "https://api.perplexity.ai/models",
        "openrouter":   "https://openrouter.ai/api/v1/models",
        "together":     "https://api.together.xyz/v1/models",
        "groq":         "https://api.groq.com/openai/v1/models",
        "google":       "https://generativelanguage.googleapis.com/v1beta/openai/models",
        "lingyi":       "https://api.lingyiwanwu.com/v1/models",
        "moonshot":     "https://api.moonshot.cn/v1/models",
        "siliconflow":  "https://api.siliconflow.cn/v1/models",
        "stepfun":      "https://api.stepfun.com/v1/models",
    }

    # Providers with known model lists (no /v1/models endpoint)
    STATIC_PROVIDERS = {
        "anthropic": "https://docs.anthropic.com/en/docs/models",
        "alibaba":   "https://help.aliyun.com/zh/model-studio/models",
        "baidu":     "https://cloud.baidu.com/doc/WENXINWORKSHOP/s/hm90w209a",
        "zhipu":     "https://open.bigmodel.cn/modelcenter",
        "doubao":    "https://www.volcengine.com/docs/82379/1330310",
        "baichuan":  "https://platform.baichuan-ai.com",
        "tencent":   "https://cloud.tencent.com/document/product/1729/104753",
        "iflytek":   "https://www.xfyun.cn/doc/spark/Web.html",
        "minimax":   "https://platform.minimax.io/docs/release-notes/models",
        "sensenova": "https://www.sensenova.cn",
        "skywork":   "https://tiangong.cn",
        "azure":     "https://portal.azure.com",
    }

    def __init__(self):
        self._cache: Dict[str, DiscoveryResult] = {}
        self._cache_time: Dict[str, float] = {}
        self._cache_ttl = 3600  # 1 hour
        self._lock = threading.Lock()
        self._discovered_models: Dict[str, DiscoveredModel] = {}

    def discover_provider(self, provider: str, api_key: Optional[str] = None,
                          base_url: Optional[str] = None,
                          use_cache: bool = True) -> DiscoveryResult:
        """Discover all models from a specific provider."""
        t0 = time.time()

        # Check cache
        if use_cache and provider in self._cache_time:
            age = time.time() - self._cache_time[provider]
            if age < self._cache_ttl:
                return self._cache[provider]

        # Determine endpoint
        endpoint = base_url or self.MODELS_ENDPOINT_PROVIDERS.get(provider)
        if not endpoint:
            url = self.STATIC_PROVIDERS.get(provider, "unknown")
            return DiscoveryResult(
                provider=provider, total_found=0, models=[],
                new_models=[], errors=[f"Static provider, no API endpoint. Docs: {url}"],
                duration_ms=(time.time() - t0) * 1000,
            )

        # Try to fetch models
        models, errors = self._fetch_models(provider, endpoint, api_key)
        discovered = self._process_models(provider, models)

        # Diff against current registry
        from laap.llm.provider import MODEL_REGISTRY
        known = set(MODEL_REGISTRY.keys())
        new_models = [m.id for m in discovered if m.id not in known]

        result = DiscoveryResult(
            provider=provider,
            total_found=len(discovered),
            models=discovered,
            new_models=new_models,
            errors=errors,
            duration_ms=(time.time() - t0) * 1000,
        )

        # Cache
        with self._lock:
            self._cache[provider] = result
            self._cache_time[provider] = time.time()
            for m in discovered:
                self._discovered_models[m.id] = m

        return result

    def discover_all(self, api_keys: Optional[Dict[str, str]] = None,
                     use_cache: bool = True) -> Dict[str, DiscoveryResult]:
        """Discover models from ALL configured providers."""
        results = {}
        import concurrent.futures

        # Determine which providers to scan
        providers_to_scan = set(self.MODELS_ENDPOINT_PROVIDERS.keys())

        # If api_keys provided, only scan those with keys
        if api_keys:
            providers_to_scan = {
                p for p in providers_to_scan
                if api_keys.get(p) or os.environ.get(
                    self._get_key_env(p), ""
                )
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            fut_to_prov = {
                pool.submit(self.discover_provider, p, use_cache=use_cache): p
                for p in providers_to_scan
            }
            for fut in concurrent.futures.as_completed(fut_to_prov):
                prov = fut_to_prov[fut]
                try:
                    results[prov] = fut.result()
                except Exception as e:
                    results[prov] = DiscoveryResult(
                        provider=prov, total_found=0, models=[],
                        new_models=[], errors=[str(e)],
                        duration_ms=0,
                    )

        return results

    def ping_model(self, model_id: str, api_key: Optional[str] = None,
                   base_url: Optional[str] = None) -> Tuple[bool, str]:
        """Test if a model ID is accessible by making a minimal API call.

        Returns (success, message)
        """
        from laap.llm.provider import MODEL_REGISTRY
        import httpx

        # Find provider info
        info = MODEL_REGISTRY.get(model_id)
        if not info:
            # Try checking by known patterns
            return False, f"Unknown model: {model_id}"

        provider = info["provider"]
        api_url = base_url or info.get("api_url", "")
        key_env = info.get("api_key_env", "")
        key = api_key or os.environ.get(key_env, "")

        if not key:
            return False, f"No API key for {provider} (set {key_env})"

        if not api_url:
            return False, f"No API URL for {provider}"

        # Make a lightweight request
        try:
            resp = httpx.post(
                f"{api_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": model_id,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1,
                    "stream": False,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                return True, f"✓ {model_id} is accessible"
            elif resp.status_code == 401:
                return False, f"Authentication failed for {model_id} (check API key)"
            elif resp.status_code == 404:
                return False, f"Model '{model_id}' not found at provider (may be outdated)"
            else:
                return False, f"HTTP {resp.status_code}: {resp.text[:100]}"
        except httpx.TimeoutException:
            return False, f"Connection timeout for {api_url}"
        except Exception as e:
            return False, str(e)

    def scan_and_diff(self, provider: str, api_key: Optional[str] = None
                      ) -> Dict[str, Any]:
        """Scan a provider and return what's new vs current registry."""
        from laap.llm.provider import MODEL_REGISTRY

        result = self.discover_provider(provider, api_key)

        known = set(MODEL_REGISTRY.keys())
        new = [m.id for m in result.models if m.id not in known]
        missing = [mid for mid in known
                   if MODEL_REGISTRY[mid]["provider"] == provider
                   and mid not in {m.id for m in result.models}]

        return {
            "provider": provider,
            "found": result.total_found,
            "new_models": new,
            "possibly_deprecated": missing,
            "errors": result.errors,
            "duration_ms": result.duration_ms,
        }

    def suggest_updates(self, provider: str,
                        api_key: Optional[str] = None) -> List[str]:
        """Suggest model ID updates for a provider."""
        diff = self.scan_and_diff(provider, api_key)
        suggestions = []

        if diff["new_models"]:
            suggestions.append(
                f"📦 New models detected for {provider}:\n  "
                + "\n  ".join(diff["new_models"][:20])
            )
        if diff["possibly_deprecated"]:
            suggestions.append(
                f"⚠️ Models no longer returned by API (may be deprecated):\n  "
                + "\n  ".join(diff["possibly_deprecated"][:10])
            )
        if diff["errors"]:
            suggestions.append(
                f"❌ Errors during scan:\n  "
                + "\n  ".join(diff["errors"][:5])
            )

        return suggestions

    def update_registry(self, provider: str,
                        api_key: Optional[str] = None) -> Dict[str, Any]:
        """Auto-update MODEL_REGISTRY with discovered models for a provider."""
        from laap.llm import provider as llm_provider

        result = self.discover_provider(provider, api_key)
        added = 0
        skipped = 0

        for model in result.models:
            mid = model.id
            if mid not in llm_provider.MODEL_REGISTRY:
                # Add to registry
                api_url = self.MODELS_ENDPOINT_PROVIDERS.get(provider, "https://api.openai.com/v1")
                key_env = self._get_key_env(provider)
                llm_provider.MODEL_REGISTRY[mid] = {
                    "provider": provider,
                    "api_url": api_url,
                    "api_key_env": key_env,
                }
                llm_provider.MODEL_LABELS[mid] = f"{provider}:{mid}"
                added += 1
            else:
                skipped += 1

        return {
            "provider": provider,
            "found": result.total_found,
            "added": added,
            "skipped": skipped,
            "total_in_registry": len(llm_provider.MODEL_REGISTRY),
        }

    def _fetch_models(self, provider: str, endpoint: str,
                      api_key: Optional[str] = None) -> Tuple[List[dict], List[str]]:
        """Fetch model list from a provider's API."""
        import httpx
        errors = []
        models_data = []

        key = api_key or os.environ.get(self._get_key_env(provider), "")

        try:
            headers = {"Content-Type": "application/json"}
            if key:
                headers["Authorization"] = f"Bearer {key}"

            resp = httpx.get(endpoint, headers=headers, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                # Handle different response formats
                if "data" in data:
                    models_data = data["data"]
                elif isinstance(data, list):
                    models_data = data
                else:
                    models_data = [data]
            else:
                errors.append(f"HTTP {resp.status_code}: {resp.text[:100]}")
        except httpx.TimeoutException:
            errors.append(f"Timeout fetching {endpoint}")
        except Exception as e:
            errors.append(str(e))

        return models_data, errors

    def _process_models(self, provider: str,
                        models_data: List[dict]) -> List[DiscoveredModel]:
        """Process raw model data into DiscoveredModel objects."""
        result = []
        seen: Set[str] = set()

        for item in models_data:
            mid = item.get("id", "") if isinstance(item, dict) else str(item)
            if not mid or mid in seen:
                continue
            seen.add(mid)

            dm = DiscoveredModel(
                id=mid,
                provider=provider,
                owned_by=item.get("owned_by", "") if isinstance(item, dict) else "",
                created=item.get("created", 0) if isinstance(item, dict) else 0,
                object_type=item.get("object", "model") if isinstance(item, dict) else "model",
            )
            result.append(dm)

        return result

    def _get_key_env(self, provider: str) -> str:
        """Get the env var name for a provider's API key."""
        from laap.llm.factory import PROVIDER_KEY_ENV
        return PROVIDER_KEY_ENV.get(provider, f"{provider.upper()}_API_KEY")

    def clear_cache(self, provider: Optional[str] = None):
        with self._lock:
            if provider:
                self._cache.pop(provider, None)
                self._cache_time.pop(provider, None)
            else:
                self._cache.clear()
                self._cache_time.clear()

    @property
    def cached_providers(self) -> List[str]:
        return list(self._cache.keys())

    @property
    def total_discovered(self) -> int:
        return len(self._discovered_models)

    def status(self) -> dict:
        return {
            "cached_providers": len(self._cache),
            "total_discovered": self.total_discovered,
            "cache_ttl_seconds": self._cache_ttl,
        }


# Global discovery engine
discovery = ModelDiscovery()
