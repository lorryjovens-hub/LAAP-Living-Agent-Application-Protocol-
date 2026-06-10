"""Cron Scheduler — 定时任务调度器"""
from __future__ import annotations
import time, json, logging, threading, os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("agent_core.cron")

@dataclass
class CronJob:
    name: str = ""
    interval: int = 3600  # seconds
    handler: Optional[Callable] = None
    last_run: float = 0.0
    enabled: bool = True
    repeat: int = -1  # -1 = forever
    run_count: int = 0

class CronScheduler:
    def __init__(self):
        self._jobs: Dict[str, CronJob] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def every(self, name: str, interval: int, handler: Callable, repeat: int = -1):
        self._jobs[name] = CronJob(name=name, interval=interval, handler=handler, repeat=repeat)
        return self
    
    def minutes(self, name: str, n: int, handler: Callable):
        return self.every(name, n * 60, handler)
    
    def hours(self, name: str, n: int, handler: Callable):
        return self.every(name, n * 3600, handler)
    
    def at(self, name: str, cron_expr: str, handler: Callable):
        """Simple cron-like scheduling (minute hour day month weekday)"""
        parts = cron_expr.split()
        if len(parts) >= 2:
            interval = 3600  # default hourly
            if parts[0] == '*':
                interval = 60
            if parts[0] != '*' and parts[1] == '*':
                interval = int(parts[0]) * 60
            self.every(name, interval, handler)
        return self
    
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"Cron scheduler started with {len(self._jobs)} jobs")
    
    def stop(self):
        self._running = False
        logger.info("Cron scheduler stopped")
    
    def _run_loop(self):
        while self._running:
            now = time.time()
            for job in self._jobs.values():
                if not job.enabled:
                    continue
                if job.repeat != -1 and job.run_count >= job.repeat:
                    continue
                if now - job.last_run >= job.interval:
                    self._execute(job)
            time.sleep(10)
    
    def _execute(self, job: CronJob):
        try:
            job.last_run = time.time()
            job.run_count += 1
            if job.handler:
                job.handler()
            logger.info(f"Cron executed: {job.name}")
        except Exception as e:
            logger.error(f"Cron {job.name} failed: {e}")
    
    def remove(self, name: str):
        self._jobs.pop(name, None)
    
    def list_jobs(self) -> List[CronJob]:
        return list(self._jobs.values())
    
    def get_stats(self) -> dict:
        return {"jobs": len(self._jobs), "running": self._running}
