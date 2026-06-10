"""Alerting System"""
from __future__ import annotations
import time, json, logging, threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("infrastructure.monitoring.alerting")

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class Alert:
    name: str = ""
    message: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    timestamp: float = field(default_factory=time.time)
    labels: Dict = field(default_factory=dict)
    acknowledged: bool = False

@dataclass
class AlertRule:
    name: str = ""
    metric_name: str = ""
    operator: str = ">"
    threshold: float = 0.0
    duration_seconds: int = 0
    severity: AlertSeverity = AlertSeverity.WARNING
    message_template: str = ""

class AlertManager:
    def __init__(self):
        self._rules: List[AlertRule] = []
        self._alerts: List[Alert] = []
        self._suppressions: Dict[str, float] = {}
        self._lock = threading.RLock()
    def add_rule(self, rule: AlertRule):
        self._rules.append(rule)
    def evaluate(self, metrics) -> List[Alert]:
        alerts = []
        for rule in self._rules:
            if rule.name in self._suppressions:
                if time.time() < self._suppressions[rule.name]:
                    continue
            value = getattr(metrics, rule.metric_name, 0) if hasattr(metrics, rule.metric_name) else 0
            triggered = False
            if rule.operator == ">" and value > rule.threshold: triggered = True
            elif rule.operator == "<" and value < rule.threshold: triggered = True
            elif rule.operator == ">=" and value >= rule.threshold: triggered = True
            elif rule.operator == "<=" and value <= rule.threshold: triggered = True
            if triggered:
                alert = Alert(name=rule.name, message=rule.message_template.format(value=value),
                            severity=rule.severity, labels={"metric": rule.metric_name, "value": value})
                alerts.append(alert)
        with self._lock:
            self._alerts.extend(alerts)
            if len(self._alerts) > 1000:
                self._alerts = self._alerts[-1000:]
        return alerts
    def acknowledge(self, alert_name: str):
        for a in self._alerts:
            if a.name == alert_name:
                a.acknowledged = True
    def suppress(self, rule_name: str, duration_seconds: int = 3600):
        self._suppressions[rule_name] = time.time() + duration_seconds
    def get_active(self) -> List[Alert]:
        return [a for a in self._alerts if not a.acknowledged]
