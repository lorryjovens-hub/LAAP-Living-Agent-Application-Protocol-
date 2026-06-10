"""Structured Logging"""
from __future__ import annotations
import time, json, logging, traceback
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional

class StructuredLogger:
    def __init__(self, name: str = "laap", level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
    def _log(self, level: str, message: str, **kwargs):
        record = {"timestamp": time.time(), "level": level, "logger": self.logger.name,
                 "message": message, "module": kwargs.pop("module", ""), **kwargs}
        getattr(self.logger, level.lower(), self.logger.info)(json.dumps(record, ensure_ascii=False))
    def info(self, message: str, **kwargs):
        self._log("info", message, **kwargs)
    def warning(self, message: str, **kwargs):
        self._log("warning", message, **kwargs)
    def error(self, message: str, **kwargs):
        self._log("error", message, **kwargs)
    def debug(self, message: str, **kwargs):
        self._log("debug", message, **kwargs)
