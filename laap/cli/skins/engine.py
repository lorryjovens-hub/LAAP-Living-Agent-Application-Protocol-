"""
LAAP — Ao Skin Engine
YAML-driven theme system for the LAAP CLI.
Inspired by Hermes skin system, simplified for LAAP's golden dragon identity.
"""

from __future__ import annotations
import json, logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("laap.cli.skins")
SKINS_DIR = Path.home() / ".laap" / "skins"


@dataclass
class Skin:
    name: str
    description: str = ""
    colors: Dict[str, str] = field(default_factory=dict)
    spinner: Dict[str, Any] = field(default_factory=dict)
    branding: Dict[str, str] = field(default_factory=dict)
    tool_prefix: str = "  "
    tool_emojis: Dict[str, str] = field(default_factory=dict)

    def get_color(self, key: str, fb: str = "") -> str:
        return self.colors.get(key, fb)

    def get_branding(self, key: str, fb: str = "") -> str:
        return self.branding.get(key, fb)


_BUILTIN = {
    "ao": {
        "colors": {"border": "#CD7F32", "title": "#FFD700", "accent": "#FFBF00",
                   "dim": "#8B6914", "text": "#FFF8DC", "ok": "#4caf50",
                   "error": "#ef5350", "warn": "#ffa726", "prompt": "#FFD700"},
        "branding": {"name": "Ao Agent", "welcome": "Ao awakens...",
                      "goodbye": "Ao returns to the mist.", "prompt_symbol": ">>"},
    },
    "mono": {
        "colors": {"border": "#555", "title": "#eee", "text": "#ccc"},
        "branding": {"name": "Ao Agent", "prompt_symbol": ">"},
    },
}


def load(name: str) -> Skin:
    user = SKINS_DIR / f"{name}.json"
    if user.is_file():
        try:
            return _build(json.loads(user.read_text("utf-8")))
        except Exception:
            pass
    if name in _BUILTIN:
        return _build(_BUILTIN[name])
    return _build(_BUILTIN.get("ao", {}))


def _build(d: dict) -> Skin:
    return Skin(name=d.get("name", "?"), description=d.get("description", ""),
                colors=d.get("colors", {}), spinner=d.get("spinner", {}),
                branding=d.get("branding", {}))


_skin = None
_name = "ao"


def get() -> Skin:
    global _skin
    if _skin is None:
        _skin = load(_name)
    return _skin


def set_active(name: str) -> Skin:
    global _skin, _name
    _name = name
    _skin = load(name)
    return _skin


def available() -> List[dict]:
    r = [{"name": n, "source": "builtin"} for n in _BUILTIN]
    SKINS_DIR.mkdir(parents=True, exist_ok=True)
    for f in sorted(SKINS_DIR.glob("*.json")):
        try:
            d = json.loads(f.read_text("utf-8"))
            r.append({"name": d["name"], "source": "user"})
        except Exception:
            pass
    return r
