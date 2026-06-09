"""LAAP — Sound Effects System

Plays audio feedback for tool completions, errors, and events.
Supports Windows (winsound), macOS (afplay), and Linux (aplay/paplay).
"""

from __future__ import annotations
import logging
import os
import subprocess
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger("laap.ui.sound")

# ── Sound Definitions ────────────────────────────────────────
# Each sound is (frequency_hz, duration_ms) for beep, or file path

SOUNDS = {
    "tool_complete": (880, 100),     # Short high beep
    "tool_error": (220, 300),        # Low long beep
    "task_done": (660, 150),         # Medium pleasant beep
    "startup": (440, 200),           # Standard startup beep
    "notification": (520, 100),      # Notification ping
    "warning": (330, 200),           # Warning tone
}


class SoundEngine:
    """Plays system sounds for UI feedback.

    Auto-detects platform and uses appropriate method.
    """

    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self._platform = self._detect_platform()

    def _detect_platform(self) -> str:
        """Detect sound capabilities."""
        if os.name == "nt":
            return "windows"
        try:
            subprocess.run(["which", "afplay"], capture_output=True, timeout=2)
            return "macos"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        try:
            subprocess.run(["which", "paplay"], capture_output=True, timeout=2)
            return "linux-pulse"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return "none"

    def play(self, sound_name: str = "tool_complete"):
        """Play a named sound asynchronously."""
        if not self._enabled:
            return

        sound = SOUNDS.get(sound_name)
        if not sound:
            return

        threading.Thread(target=self._play_sync, args=(sound,), daemon=True).start()

    def _play_sync(self, sound):
        """Play sound (blocking, runs in thread)."""
        try:
            if self._platform == "windows":
                import winsound
                freq, dur = sound
                winsound.Beep(freq, dur)
            elif self._platform == "macos":
                # Generate and play a simple sine wave via afplay
                freq, dur = sound
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    self._generate_wav(f, freq, dur)
                    tmp = f.name
                subprocess.run(["afplay", tmp], capture_output=True, timeout=2)
                os.unlink(tmp)
            elif self._platform == "linux-pulse":
                freq, dur = sound
                subprocess.run(
                    ["paplay", "--volume=32768",
                     f"/usr/share/sounds/freedesktop/stereo/complete.oga"],
                    capture_output=True, timeout=2,
                )
        except Exception as e:
            logger.debug(f"Sound play error: {e}")

    def _generate_wav(self, fileobj, freq: int, duration_ms: int):
        """Generate a simple sine wave WAV file."""
        import struct
        import math

        sample_rate = 22050
        num_samples = int(sample_rate * duration_ms / 1000)
        # WAV header
        fileobj.write(b"RIFF")
        fileobj.write(struct.pack("<I", 36 + num_samples * 2))
        fileobj.write(b"WAVE")
        fileobj.write(b"fmt ")
        fileobj.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
        fileobj.write(b"data")
        fileobj.write(struct.pack("<I", num_samples * 2))

        for i in range(num_samples):
            t = i / sample_rate
            value = int(16000 * math.sin(2 * math.pi * freq * t))
            fileobj.write(struct.pack("<h", value))

    def set_enabled(self, enabled: bool):
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def platform(self) -> str:
        return self._platform


# Singleton
_sound_engine: Optional[SoundEngine] = None

def get_sound_engine() -> SoundEngine:
    global _sound_engine
    if _sound_engine is None:
        _sound_engine = SoundEngine()
    return _sound_engine


def play(sound_name: str = "tool_complete"):
    """Play a sound (convenience function)."""
    get_sound_engine().play(sound_name)
