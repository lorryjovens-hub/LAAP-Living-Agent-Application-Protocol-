"""Theme System — Golden Dragon主题"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class ColorSchema:
    primary: str = "#D4AF37"
    secondary: str = "#8B0000"
    background: str = "#1A1A2E"
    surface: str = "#16213E"
    text: str = "#E8D5B7"
    text_secondary: str = "#A0A0B0"
    accent: str = "#FF6B35"
    success: str = "#00C853"
    warning: str = "#FFD600"
    error: str = "#FF1744"
    info: str = "#2979FF"

@dataclass
class Typography:
    font_family: str = "'Consolas', 'Courier New', monospace"
    font_size_sm: str = "12px"
    font_size_md: str = "14px"
    font_size_lg: str = "16px"
    font_size_xl: str = "20px"
    font_size_xxl: str = "28px"
    line_height: float = 1.5

@dataclass
class Spacing:
    xs: str = "4px"
    sm: str = "8px"
    md: str = "12px"
    lg: str = "16px"
    xl: str = "24px"
    xxl: str = "32px"

class Theme:
    def __init__(self, name: str = "golden_dragon"):
        self.name = name
        self.colors = ColorSchema()
        self.typography = Typography()
        self.spacing = Spacing()
        self.border_radius = "8px"
        self.animation_duration = "0.3s"
    def as_css_variables(self) -> str:
        vars = []
        for key, val in self.colors.__dict__.items():
            vars.append(f"  --laap-color-{key}: {val};")
        return ":root {\n" + chr(10).join(vars) + "\n}"
    def dark_mode(self):
        self.colors.background = "#0D0D1A"
        self.colors.surface = "#1A1A2E"
        return self

class ThemeManager:
    _themes: Dict[str, Theme] = {}
    @classmethod
    def register(cls, name: str, theme: Theme):
        cls._themes[name] = theme
    @classmethod
    def get(cls, name: str = "golden_dragon") -> Theme:
        return cls._themes.get(name, Theme())
