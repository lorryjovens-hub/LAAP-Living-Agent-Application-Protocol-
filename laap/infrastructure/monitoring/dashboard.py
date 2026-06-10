"""Dashboard Data Provider"""
from __future__ import annotations
import time, json, logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("infrastructure.monitoring.dashboard")

@dataclass
class DashboardPanel:
    title: str = ""
    metric: str = ""
    chart_type: str = "line"
    width: int = 6
    height: int = 4

class DashboardDataProvider:
    def __init__(self):
        self._panels: List[DashboardPanel] = []
    def add_panel(self, panel: DashboardPanel):
        self._panels.append(panel)
    def get_layout(self) -> List[Dict]:
        return [{"title": p.title, "metric": p.metric, "type": p.chart_type, "w": p.width, "h": p.height}
                for p in self._panels]
    def get_grafana_json(self) -> str:
        panels = []
        for i, p in enumerate(self._panels):
            panels.append({
                "id": i, "title": p.title, "type": "graph",
                "gridPos": {"x": (i % 4) * 6, "y": i // 4 * 4, "w": p.width, "h": p.height},
                "targets": [{"expr": p.metric, "legendFormat": "{{label}}"}]
            })
        return json.dumps({"title": "LAAP Dashboard", "panels": panels}, indent=2)
