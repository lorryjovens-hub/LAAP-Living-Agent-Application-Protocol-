"""
LAAP — Ao Cron Scheduler
Background task scheduler for recurring LAAP operations.
Inspired by Hermes cron system.
"""

from __future__ import annotations
import json, logging, threading, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("laap.cron")

CRON_DIR = Path.home() / ".laap" / "cron"


@dataclass
class CronJob:
    id: str
    name: str
    interval_seconds: int
    task: str
    enabled: bool = True
    last_run: float = 0
    run_count: int = 0
    error_count: int = 0


class CronScheduler:
    """Lightweight cron scheduler for LAAP."""

    def __init__(self, runner: Optional[Callable[[str], None]] = None):
        CRON_DIR.mkdir(parents=True, exist_ok=True)
        self.jobs: Dict[str, CronJob] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.runner = runner
        self._load()

    def _load(self):
        path = CRON_DIR / "jobs.json"
        if path.exists():
            try:
                data = json.loads(path.read_text("utf-8"))
                for d in data:
                    j = CronJob(**d)
                    self.jobs[j.id] = j
            except Exception as e:
                logger.warning("Cron load: %s", e)

    def _save(self):
        path = CRON_DIR / "jobs.json"
        path.write_text(json.dumps([j.__dict__ for j in self.jobs.values()], indent=2), "utf-8")

    def add(self, name: str, interval_seconds: int, task: str) -> str:
        import uuid
        jid = str(uuid.uuid4())[:8]
        self.jobs[jid] = CronJob(id=jid, name=name, interval_seconds=interval_seconds, task=task)
        self._save()
        logger.info("Cron: %s (%s) every %ds", name, jid, interval_seconds)
        return jid

    def remove(self, jid: str) -> bool:
        if jid in self.jobs:
            self.jobs[jid].enabled = False
            self._save()
            return True
        return False

    def list(self) -> List[dict]:
        return [{"id": j.id, "name": j.name, "interval": j.interval_seconds,
                 "enabled": j.enabled, "runs": j.run_count, "errors": j.error_count}
                for j in self.jobs.values()]

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Cron started")

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            now = time.time()
            for j in self.jobs.values():
                if j.enabled and now - j.last_run >= j.interval_seconds:
                    try:
                        logger.info("Cron running: %s", j.name)
                        if self.runner:
                            result = self.runner(j.task)
                            logger.info("Cron %s: %s", j.name, str(result)[:200])
                        else:
                            logger.warning("Cron %s: no runner set, skipping task", j.name)
                        j.run_count += 1
                        j.last_run = now
                        self._save()
                    except Exception as e:
                        j.error_count += 1
                        logger.error("Cron %s: %s", j.name, e)
            time.sleep(5)
