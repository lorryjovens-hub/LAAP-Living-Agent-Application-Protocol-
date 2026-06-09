"""
LAAP — Plugin Manager
Plugin discovery, loading, and lifecycle management.
"""

from __future__ import annotations
import importlib, logging, pkgutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("laap.plugins")

PLUGIN_DIR = Path.home() / ".laap" / "plugins"


class PluginManager:
    """LAAP plugin system — discovers and loads plugins."""

    def __init__(self):
        self._plugins: Dict[str, Any] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._discover()

    def _discover(self):
        """Find installed LAAP plugins."""
        PLUGIN_DIR.mkdir(parents=True, exist_ok=True)

        # Scan laap.plugins namespace
        try:
            import laap.plugins
            for mod in pkgutil.iter_modules(laap.plugins.__path__, prefix="laap.plugins."):
                try:
                    m = importlib.import_module(mod.name)
                    if hasattr(m, "setup"):
                        m.setup(self)
                        name = mod.name.split(".")[-1]
                        self._plugins[name] = m
                        logger.info("Plugin: %s", name)
                except Exception as e:
                    logger.debug("Plugin load %s: %s", mod.name, e)
        except Exception:
            pass

    def register_hook(self, event: str, handler: Callable):
        self._hooks.setdefault(event, []).append(handler)

    def trigger(self, event: str, **kwargs):
        for handler in self._hooks.get(event, []):
            try:
                handler(**kwargs)
            except Exception as e:
                logger.error("Hook %s/%s: %s", event, handler.__name__, e)

    def list(self) -> List[dict]:
        return [{"name": n, "hooks": list(self._hooks.keys())} for n in self._plugins]
