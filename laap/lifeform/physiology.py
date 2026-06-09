"""LAAP — Digital Physiology Engine

Vital signs, energy cycles, growth stages, and emotional state.
"""
from __future__ import annotations
import json, logging, math, os, time, threading
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("laap.lifeform.physiology")
STATE_DIR = Path.home() / ".laap" / "lifeform"


@dataclass
class VitalSigns:
    energy: float = 1.0        # 0-1: Physical energy
    focus: float = 1.0         # 0-1: Mental focus
    mood: float = 0.7          # 0-1: Emotional state
    curiosity: float = 0.8     # 0-1: Drive to explore
    sociability: float = 0.5   # 0-1: Social drive

    ENERGY_COST_PER_TOOL = 0.02
    FOCUS_DECAY_PER_TURN = 0.01
    RECOVERY_PER_HOUR = 0.08


class PhysiologyEngine:
    """Manages the digital lifeform's vital signs and growth."""

    def __init__(self):
        self.vitals = VitalSigns()
        self.level = 1
        self.xp = 0
        self.growth_stage = "adolescent"  # baby → adolescent → mature → sage
        self._lock = threading.RLock()
        self._last_tick = time.time()
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._load()

    def _state_path(self) -> Path:
        return STATE_DIR / "physiology.json"

    def _load(self):
        path = self._state_path()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self.level = data.get("level", 1)
                self.xp = data.get("xp", 0)
                self.growth_stage = data.get("growth_stage", "adolescent")
                if "vitals" in data:
                    self.vitals = VitalSigns(**data["vitals"])
            except Exception:
                pass

    def _save(self):
        try:
            data = {
                "level": self.level, "xp": self.xp,
                "growth_stage": self.growth_stage,
                "vitals": self.vitals.__dict__,
            }
            self._state_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def tick(self):
        """Time-based update of all vital signs."""
        now = time.time()
        dt_hours = (now - self._last_tick) / 3600
        self._last_tick = now
        if dt_hours <= 0:
            return

        with self._lock:
            hour = datetime.now().hour
            if 7 <= hour <= 23:  # Awake: slow recovery
                self.vitals.energy = min(1.0, self.vitals.energy + 0.03 * dt_hours)
            else:  # Sleep: fast recovery
                self.vitals.energy = min(1.0, self.vitals.energy + 0.12 * dt_hours)

            self.vitals.focus = min(1.0, self.vitals.focus + 0.02 * dt_hours)
            self.vitals.mood = max(0.0, min(1.0, self.vitals.mood + 0.01 * dt_hours))

    def work(self, difficulty: float = 0.5, success: bool = True):
        """Expend energy on work."""
        with self._lock:
            self.tick()
            cost = difficulty * self.vitals.ENERGY_COST_PER_TOOL
            self.vitals.energy = max(0.0, self.vitals.energy - cost)
            self.vitals.focus = max(0.0, self.vitals.focus - self.vitals.FOCUS_DECAY_PER_TURN)
            if success:
                self.vitals.mood = min(1.0, self.vitals.mood + 0.02)
                self.xp += max(1, int(difficulty * 15))
            else:
                self.vitals.mood = max(0.0, self.vitals.mood - 0.05)
            self._check_level_up()

    def _check_level_up(self):
        needed = self.level * 80
        if self.xp >= needed:
            self.level += 1
            self.xp -= needed
            if self.level >= 5 and self.growth_stage == "adolescent":
                self.growth_stage = "mature"
            elif self.level >= 20:
                self.growth_stage = "sage"
            self._save()
            return True
        return False

    def is_tired(self) -> bool:
        return self.vitals.energy < 0.2 or self.vitals.focus < 0.2

    def rest(self, hours: float = 1.0):
        """Recover by resting."""
        self.vitals.energy = min(1.0, self.vitals.energy + hours * self.vitals.RECOVERY_PER_HOUR)
        self.vitals.focus = min(1.0, self.vitals.focus + hours * 0.05)
        self._save()

    def to_dict(self) -> dict:
        return {
            "vitals": {k: round(v, 2) for k, v in self.vitals.__dict__.items()},
            "level": self.level, "xp": self.xp,
            "stage": self.growth_stage,
            "tired": self.is_tired(),
        }

    def status_line(self) -> str:
        v = self.vitals
        energy_bar = "█" * int(v.energy * 20) + "░" * (20 - int(v.energy * 20))
        return f"❤️  E:{energy_bar} Lv.{self.level} {self.growth_stage} | mood={v.mood:.2f} focus={v.focus:.2f}"
