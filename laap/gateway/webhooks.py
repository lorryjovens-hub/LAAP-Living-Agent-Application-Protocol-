"""LAAP — Webhook Subscription Manager
JSON-config backed webhook management with HMAC signing and event filtering.
Config at ~/.laap/webhooks/config.json
"""
from __future__ import annotations
import hashlib, hmac, json, logging, os, secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("laap.gateway.webhooks")
CONFIG_DIR = Path.home() / ".laap" / "webhooks"
CONFIG_FILE = CONFIG_DIR / "config.json"

class WebhookNotFoundError(Exception): pass
class WebhookValidationError(Exception): pass

class WebhookManager:
    """Manage webhook subscriptions backed by JSON config."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_FILE
        self._config = self._load()

    def _load(self) -> dict:
        if self.config_path.exists():
            try:
                raw = json.loads(self.config_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and "subscriptions" in raw:
                    return raw
            except (json.JSONDecodeError, OSError):
                pass
        return {"subscriptions": {}}

    def _save(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(self._config, indent=2, ensure_ascii=False), encoding="utf-8")

    def _subs(self) -> dict:
        return self._config.setdefault("subscriptions", {})

    def subscribe(self, name: str, url: str, event_type: str = "*", secret: Optional[str] = None) -> dict:
        subs = self._subs()
        sub = {
            "name": name, "url": url, "event_type": event_type,
            "secret": secret or secrets.token_hex(32),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True,
        }
        subs[name] = sub
        self._save()
        logger.info("Subscribed webhook '%s' -> %s (event=%s)", name, url, event_type)
        return {k: v for k, v in sub.items() if k != "secret"}

    def list(self) -> List[dict]:
        return [{k: v for k, v in sub.items() if k != "secret"} for sub in self._subs().values()]

    def get(self, name: str) -> Optional[dict]:
        sub = self._subs().get(name)
        if sub is None:
            return None
        return {k: v for k, v in sub.items() if k != "secret"}

    def remove(self, name: str) -> bool:
        subs = self._subs()
        if name not in subs:
            raise WebhookNotFoundError(f"Webhook '{name}' not found")
        del subs[name]
        self._save()
        logger.info("Removed webhook '%s'", name)
        return True

    def test(self, name: str, timeout: int = 10) -> dict:
        subs = self._subs()
        if name not in subs:
            raise WebhookNotFoundError(f"Webhook '{name}' not found")
        sub = subs[name]
        payload = {"event": "test", "subscription": name, "timestamp": datetime.now(timezone.utc).isoformat()}
        return self._send(sub, payload, timeout)

    def trigger(self, event_type: str, payload: dict) -> List[dict]:
        results = []
        subs = self._subs()
        envelope = {"event": event_type, "timestamp": datetime.now(timezone.utc).isoformat(), "payload": payload}
        for name, sub in list(subs.items()):
            if not sub.get("active", True):
                continue
            if sub.get("event_type", "*") not in (event_type, "*"):
                continue
            try:
                results.append(self._send(sub, envelope))
            except Exception as exc:
                results.append({"name": name, "success": False, "error": str(exc)})
        return results

    @staticmethod
    def _sign(secret: str, body: bytes) -> str:
        return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    def _send(self, sub: dict, payload: dict, timeout: int = 10) -> dict:
        import json as _json
        body = _json.dumps(payload, ensure_ascii=False).encode("utf-8")
        sig = self._sign(sub["secret"], body)
        headers = {
            "Content-Type": "application/json", "X-Webhook-Signature": sig,
            "X-Webhook-Event": payload.get("event", ""),
            "X-Webhook-Timestamp": payload.get("timestamp", ""),
            "User-Agent": "LAAP-Webhook/1.0",
        }
        try:
            import requests
            resp = requests.post(sub["url"], data=body, headers=headers, timeout=timeout)
            return {"name": sub["name"], "success": resp.ok, "status_code": resp.status_code, "url": sub["url"]}
        except ImportError:
            logger.warning("requests not installed, skipping webhook delivery")
            return {"name": sub["name"], "success": False, "error": "requests not installed"}
        except Exception as exc:
            logger.error("Webhook delivery to %s failed: %s", sub["url"], exc)
            return {"name": sub["name"], "success": False, "error": str(exc), "url": sub["url"]}

    @staticmethod
    def verify_signature(secret: str, body: bytes, signature_header: str) -> bool:
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header)

_default_manager: Optional[WebhookManager] = None
def get_manager() -> WebhookManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = WebhookManager()
    return _default_manager
