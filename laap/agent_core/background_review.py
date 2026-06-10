"""BackgroundReview — 异步代码审查"""
from __future__ import annotations
import time, json, logging, threading, os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("agent_core.background_review")

@dataclass
class ReviewResult:
    file_path: str = ""
    issues: List[Dict] = field(default_factory=list)
    score: float = 1.0
    summary: str = ""
    duration_ms: float = 0.0

class BackgroundReviewer:
    def __init__(self):
        self._queue: List[str] = []
        self._results: Dict[str, ReviewResult] = {}
        self._thread: Optional[threading.Thread] = None
        self._running = False
    
    def submit(self, file_path: str):
        self._queue.append(file_path)
        if not self._running:
            self._start()
    
    def _start(self):
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
    
    def _process_loop(self):
        while self._queue:
            fp = self._queue.pop(0)
            self._review_file(fp)
        self._running = False
    
    def _review_file(self, file_path: str) -> ReviewResult:
        start = time.time()
        issues = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            for i, line in enumerate(lines, 1):
                if len(line) > 200:
                    issues.append({"line": i, "severity": "warning", "msg": f"Line too long ({len(line)} chars)"})
                if 'TODO' in line:
                    issues.append({"line": i, "severity": "info", "msg": "TODO found"})
                if 'FIXME' in line:
                    issues.append({"line": i, "severity": "warning", "msg": "FIXME found"})
                if 'import *' in line:
                    issues.append({"line": i, "severity": "error", "msg": "Wildcard import"})
            score = max(0.0, 1.0 - len(issues) * 0.05)
            result = ReviewResult(file_path=file_path, issues=issues, score=score,
                                 summary=f"{len(issues)} issues",
                                 duration_ms=(time.time()-start)*1000)
        except Exception as e:
            result = ReviewResult(file_path=file_path, score=0.0, summary=str(e))
        self._results[file_path] = result
        return result
    
    def get_result(self, file_path: str) -> Optional[ReviewResult]:
        return self._results.get(file_path)
    
    def get_stats(self) -> dict:
        return {"queued": len(self._queue), "completed": len(self._results)}
