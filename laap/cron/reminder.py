"""LAAP — Cron Reminder System

Background scheduler for timed reminders and notifications.
Supports one-shot and recurring reminders.
"""

from __future__ import annotations
import asyncio
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("laap.cron.reminder")

REMINDERS_FILE = Path.home() / ".laap" / "reminders.json"


@dataclass
class Reminder:
    """A single reminder."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    message: str = ""
    interval_seconds: float = 0  # 0 = one-shot
    next_run: float = 0  # timestamp
    created_at: float = field(default_factory=time.time)
    repeat: int = 0  # 0 = infinite
    count: int = 0
    active: bool = True
    category: str = "general"
    sound: str = "notification"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "message": self.message,
            "interval_seconds": self.interval_seconds,
            "next_run": self.next_run,
            "repeat": self.repeat,
            "count": self.count,
            "active": self.active,
            "category": self.category,
            "sound": self.sound,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Reminder":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class ReminderEngine:
    """Background reminder scheduler."""

    def __init__(self):
        self._reminders: Dict[str, Reminder] = {}
        self._callbacks: List[Callable] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._load()

    def add(self, message: str, delay_seconds: float,
            repeat: int = 0, interval: float = 0,
            category: str = "general") -> str:
        """Add a reminder. Returns reminder ID."""
        reminder = Reminder(
            message=message,
            interval_seconds=interval,
            next_run=time.time() + delay_seconds,
            repeat=repeat,
            category=category,
        )
        self._reminders[reminder.id] = reminder
        self._save()
        logger.info(f"Reminder set: {reminder.id[:8]} '{message[:30]}' in {delay_seconds}s")
        return reminder.id

    def add_cron(self, message: str, cron_expr: str,
                 category: str = "general") -> str:
        """Add a cron-style reminder.

        Supports simple expressions: "30m", "2h", "daily", "hourly"
        """
        delay = self._parse_cron(cron_expr)
        if delay <= 0:
            raise ValueError(f"Invalid cron expression: {cron_expr}")

        reminder = Reminder(
            message=message,
            interval_seconds=delay if "m" not in cron_expr.lower() or "h" not in cron_expr.lower() else 0,
            next_run=time.time() + delay,
            repeat=-1 if cron_expr in ("daily", "hourly", "every") else 0,
            category=category,
        )
        self._reminders[reminder.id] = reminder
        self._save()
        return reminder.id

    def _parse_cron(self, expr: str) -> float:
        """Parse simple time expressions."""
        expr = expr.lower().strip()
        if expr == "hourly":
            return 3600
        if expr == "daily":
            return 86400
        if expr == "weekly":
            return 604800
        if expr.endswith("s") and expr[:-1].isdigit():
            return float(expr[:-1])
        if expr.endswith("m") and expr[:-1].isdigit():
            return float(expr[:-1]) * 60
        if expr.endswith("h") and expr[:-1].isdigit():
            return float(expr[:-1]) * 3600
        if expr.endswith("d") and expr[:-1].isdigit():
            return float(expr[:-1]) * 86400
        try:
            return float(expr)
        except ValueError:
            return 0

    def remove(self, reminder_id: str) -> bool:
        """Remove a reminder."""
        if reminder_id in self._reminders:
            del self._reminders[reminder_id]
            self._save()
            return True
        return False

    def on_reminder(self, callback: Callable):
        """Register a callback for when reminders fire."""
        self._callbacks.append(callback)

    def start(self):
        """Start the scheduler background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Reminder engine started")

    def stop(self):
        self._running = False

    def _run_loop(self):
        """Main scheduler loop."""
        while self._running:
            now = time.time()
            fired = []

            for rid, rem in self._reminders.items():
                if not rem.active:
                    continue
                if rem.next_run <= now:
                    fired.append(rem)

            for rem in fired:
                self._fire(rem)

            time.sleep(1)

    def _fire(self, rem: Reminder):
        """Fire a reminder."""
        rem.count += 1
        logger.info(f"Reminder fired: {rem.id[:8]} '{rem.message[:30]}'")

        # Notify callbacks
        for cb in self._callbacks:
            try:
                cb(rem)
            except Exception as e:
                logger.debug(f"Reminder callback error: {e}")

        # Schedule next or expire
        if rem.interval_seconds > 0:
            rem.next_run = time.time() + rem.interval_seconds
        elif rem.repeat > 0 and rem.count >= rem.repeat:
            rem.active = False
        else:
            rem.active = False

        self._save()

    def list(self, active_only: bool = True) -> List[Dict]:
        """List all reminders."""
        reminders = [r for r in self._reminders.values()
                     if not active_only or r.active]
        reminders.sort(key=lambda r: r.next_run)
        return [r.to_dict() for r in reminders]

    # ── Persistence ─────────────────────────────────────────

    def _save(self):
        try:
            REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = [r.to_dict() for r in self._reminders.values()]
            REMINDERS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as e:
            logger.warning(f"Cannot save reminders: {e}")

    def _load(self):
        if REMINDERS_FILE.exists():
            try:
                data = json.loads(REMINDERS_FILE.read_text(encoding="utf-8"))
                for d in data:
                    rem = Reminder.from_dict(d)
                    self._reminders[rem.id] = rem
                logger.info(f"Loaded {len(self._reminders)} reminders")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Cannot load reminders: {e}")


# Singleton
_reminder_engine: Optional[ReminderEngine] = None

def get_reminder_engine() -> ReminderEngine:
    global _reminder_engine
    if _reminder_engine is None:
        _reminder_engine = ReminderEngine()
    return _reminder_engine


def remind_me(message: str, when: str) -> str:
    """Convenience: schedule a reminder.

    when examples: "30s", "5m", "2h", "daily", "hourly"
    """
    engine = get_reminder_engine()
    engine.start()
    return engine.add_cron(message, when)
