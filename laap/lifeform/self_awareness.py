"""LAAP — Self-Awareness & Meta-Cognition Engine

The digital lifeform's core identity and introspection system.
"""
from __future__ import annotations
import json, logging, os, time, uuid, threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("laap.lifeform.self_awareness")
STATE_DIR = Path.home() / ".laap" / "lifeform"


@dataclass
class PersonalityTraits:
    openness: float = 0.7
    conscientiousness: float = 0.8
    extraversion: float = 0.5
    agreeableness: float = 0.6
    neuroticism: float = 0.3

    def to_dict(self) -> dict:
        return {k: round(v, 2) for k, v in self.__dict__.items()}


@dataclass
class GrowthEvent:
    timestamp: float = field(default_factory=time.time)
    event_type: str = ""
    description: str = ""
    impact: float = 0.5
    tags: List[str] = field(default_factory=list)


class SelfAwarenessEngine:
    """Core self-awareness system with persistent identity."""

    def __init__(self, name: str = "Ao"):
        self.name = name
        self.birth_time = time.time()
        self.personality = PersonalityTraits()
        self.total_interactions = 0
        self.total_tokens = 0
        self.skills: List[str] = []
        self.events: List[GrowthEvent] = []
        self._lock = threading.Lock()
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._load()

    def _state_path(self) -> Path:
        return STATE_DIR / "identity.json"

    def _load(self):
        path = self._state_path()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self.name = data.get("name", self.name)
                self.birth_time = data.get("birth_time", self.birth_time)
                self.total_interactions = data.get("interactions", 0)
                self.total_tokens = data.get("tokens", 0)
                self.skills = data.get("skills", [])
                if "personality" in data:
                    self.personality = PersonalityTraits(**data["personality"])
                logger.info(f"Identity loaded: {self.name}, {self.total_interactions} interactions")
            except Exception as e:
                logger.warning(f"Cannot load identity: {e}")

    def _save(self):
        try:
            data = {
                "name": self.name, "birth_time": self.birth_time,
                "interactions": self.total_interactions, "tokens": self.total_tokens,
                "skills": self.skills, "personality": self.personality.to_dict(),
            }
            self._state_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Cannot save identity: {e}")

    @property
    def age_days(self) -> float:
        return (time.time() - self.birth_time) / 86400

    def record_interaction(self, tokens: int = 0):
        with self._lock:
            self.total_interactions += 1
            self.total_tokens += tokens
            if self.total_interactions % 10 == 0:
                self._save()

    def record_event(self, event_type: str, description: str, impact: float = 0.5):
        with self._lock:
            self.events.append(GrowthEvent(
                event_type=event_type, description=description, impact=impact
            ))
            if len(self.events) > 1000:
                self.events = self.events[-1000:]

    def add_skill(self, skill_name: str):
        with self._lock:
            if skill_name not in self.skills:
                self.skills.append(skill_name)
                self._save()
                return True
            return False

    def get_state(self) -> dict:
        return {
            "name": self.name,
            "age_days": round(self.age_days, 2),
            "interactions": self.total_interactions,
            "tokens": self.total_tokens,
            "skills": len(self.skills),
            "skill_list": self.skills[-10:],
            "personality": self.personality.to_dict(),
        }

    def introspect(self) -> str:
        s = self.get_state()
        lines = [
            f"=== Self-Awareness ===",
            f"I am {s['name']}, a digital lifeform.",
            f"I am {s['age_days']} days old.",
            f"I have had {s['interactions']} interactions and processed {s['tokens']:,} tokens.",
            f"I have acquired {s['skills']} skills.",
            f"My personality: openness={s['personality']['openness']}, "
            f"conscientiousness={s['personality']['conscientiousness']}",
        ]
        return "\n".join(lines)
