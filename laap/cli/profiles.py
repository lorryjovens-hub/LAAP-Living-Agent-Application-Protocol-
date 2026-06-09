"""LAAP — Profile Manager
Multiple isolated profiles, each with its own config, env, sessions, and skills."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


LAAP_HOME = Path.home() / ".laap"
PROFILES_DIR = LAAP_HOME / "profiles"
ACTIVE_PROFILE_FILE = LAAP_HOME / "active_profile"
DEFAULT_PROFILE_NAME = "default"


def _get_profile_dir(name: str) -> Path:
    return PROFILES_DIR / name


def _profile_exists(name: str) -> bool:
    return _get_profile_dir(name).is_dir()


def _read_active_profile() -> Optional[str]:
    if ACTIVE_PROFILE_FILE.exists():
        return ACTIVE_PROFILE_FILE.read_text(encoding="utf-8").strip()
    return None


def _write_active_profile(name: str) -> None:
    ACTIVE_PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_PROFILE_FILE.write_text(name.strip(), encoding="utf-8")


def _ensure_default_profile() -> None:
    default_dir = _get_profile_dir(DEFAULT_PROFILE_NAME)
    if default_dir.is_dir():
        return
    default_dir.mkdir(parents=True, exist_ok=True)
    (default_dir / "config.yaml").write_text("# LAAP Profile Config\n", encoding="utf-8")
    (default_dir / ".env").write_text("# LAAP Environment\n", encoding="utf-8")
    (default_dir / "sessions").mkdir(exist_ok=True)
    (default_dir / "skills").mkdir(exist_ok=True)
    if not _read_active_profile():
        _write_active_profile(DEFAULT_PROFILE_NAME)


class ProfileManager:
    """Manage isolated LAAP profiles.

    Each profile lives under ~/.laap/profiles/<name>/ and contains:
        config.yaml        - Profile-specific configuration
        .env               - Environment variables
        sessions/          - Session state (SQLite)
        skills/            - Profile-specific skill files

    The active profile is tracked via ~/.laap/active_profile.
    """

    def __init__(self) -> None:
        _ensure_default_profile()

    def create(self, name: str, clone_from: Optional[str] = None) -> Dict[str, Any]:
        self._validate_name(name)
        if _profile_exists(name):
            return {"status": "error", "message": f"Profile '{name}' already exists."}
        prof_dir = _get_profile_dir(name)
        prof_dir.mkdir(parents=True, exist_ok=True)
        if clone_from:
            src_dir = _get_profile_dir(clone_from)
            if not src_dir.is_dir():
                shutil.rmtree(prof_dir, ignore_errors=True)
                return {"status": "error", "message": f"Source profile '{clone_from}' not found."}
            self._copy_profile(src_dir, prof_dir)
            msg = f"Profile '{name}' created (cloned from '{clone_from}')."
        else:
            (prof_dir / "config.yaml").write_text(f"# LAAP Profile Config - {name}\n", encoding="utf-8")
            (prof_dir / ".env").write_text(f"# LAAP Environment - {name}\n", encoding="utf-8")
            (prof_dir / "sessions").mkdir(exist_ok=True)
            (prof_dir / "skills").mkdir(exist_ok=True)
            msg = f"Profile '{name}' created."
        return {"status": "ok", "message": msg, "name": name}

    def list(self) -> List[Dict[str, Any]]:
        _ensure_default_profile()
        profiles: List[Dict[str, Any]] = []
        active = self.get_active()
        if PROFILES_DIR.is_dir():
            for entry in sorted(PROFILES_DIR.iterdir()):
                if entry.is_dir() and not entry.name.startswith("."):
                    profiles.append(self._profile_info(entry.name, active))
        return profiles

    def delete(self, name: str, *, force: bool = False) -> Dict[str, Any]:
        if not _profile_exists(name):
            return {"status": "error", "message": f"Profile '{name}' not found."}
        if name == DEFAULT_PROFILE_NAME:
            return {"status": "error", "message": "Cannot delete the default profile."}
        if not force:
            return {"status": "confirm", "message": f"Are you sure you want to delete profile '{name}'?"}
        shutil.rmtree(_get_profile_dir(name), ignore_errors=True)
        if _read_active_profile() == name:
            _write_active_profile(DEFAULT_PROFILE_NAME)
        return {"status": "ok", "message": f"Profile '{name}' deleted."}

    def switch(self, name: str) -> Dict[str, Any]:
        if not _profile_exists(name):
            return {"status": "error", "message": f"Profile '{name}' not found."}
        _write_active_profile(name)
        self._apply_profile_env(name)
        return {"status": "ok", "message": f"Switched to profile '{name}'.", "name": name}

    def show(self, name: str) -> Dict[str, Any]:
        if not _profile_exists(name):
            return {"status": "error", "message": f"Profile '{name}' not found."}
        active = self.get_active()
        info = self._profile_info(name, active)
        return {"status": "ok", "profile": info}

    def export(self, name: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        if not _profile_exists(name):
            return {"status": "error", "message": f"Profile '{name}' not found."}
        prof_dir = _get_profile_dir(name)
        if output_path is None:
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(os.getcwd(), f"{name}_{date_str}.tar.gz")
        output_path = os.path.abspath(output_path)
        with tarfile.open(output_path, "w:gz") as tar:
            tar.add(prof_dir, arcname=name)
        size = os.path.getsize(output_path)
        return {"status": "ok", "message": f"Profile '{name}' exported to {output_path} ({self._format_size(size)}).", "file": output_path}

    def import_from(self, file_path: str) -> Dict[str, Any]:
        file_path = os.path.abspath(file_path)
        if not os.path.isfile(file_path):
            return {"status": "error", "message": f"File not found: {file_path}"}
        if not tarfile.is_tarfile(file_path):
            return {"status": "error", "message": f"Not a valid tar archive: {file_path}"}
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(file_path, "r:gz") as tar:
                tar.extractall(path=tmpdir)
            items = os.listdir(tmpdir)
            if not items:
                return {"status": "error", "message": "Archive is empty - no profile data found."}
            profile_name = items[0]
            extracted_dir = os.path.join(tmpdir, profile_name)
            if not os.path.isdir(extracted_dir):
                return {"status": "error", "message": f"Expected a directory '{profile_name}' in the archive."}
            target_name = profile_name
            if _profile_exists(target_name):
                base = target_name
                counter = 1
                while _profile_exists(f"{base}_imported_{counter}"):
                    counter += 1
                target_name = f"{base}_imported_{counter}"
            shutil.copytree(extracted_dir, _get_profile_dir(target_name), dirs_exist_ok=True)
            return {"status": "ok", "message": f"Profile imported as '{target_name}'.", "name": target_name}

    def get_active(self) -> str:
        _ensure_default_profile()
        active = _read_active_profile()
        if active and _profile_exists(active):
            return active
        _write_active_profile(DEFAULT_PROFILE_NAME)
        return DEFAULT_PROFILE_NAME

    def get_active_dir(self) -> Path:
        return _get_profile_dir(self.get_active())

    def get_profile_dir(self, name: str) -> Optional[Path]:
        d = _get_profile_dir(name)
        return d if d.is_dir() else None

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or not name.strip():
            raise ValueError("Profile name cannot be empty.")
        if not all(c.isalnum() or c in "-_" for c in name):
            raise ValueError("Profile name must contain only letters, digits, hyphens, and underscores.")
        if name.startswith("."):
            raise ValueError("Profile name cannot start with a dot.")

    @staticmethod
    def _copy_profile(src: Path, dst: Path) -> None:
        for item in src.iterdir():
            s = dst / item.name
            if item.is_dir():
                shutil.copytree(item, s, dirs_exist_ok=True)
            else:
                shutil.copy2(item, s)

    @staticmethod
    def _profile_info(name: str, active_name: str) -> Dict[str, Any]:
        prof_dir = _get_profile_dir(name)
        info: Dict[str, Any] = {"name": name, "active": name == active_name, "path": str(prof_dir), "exists": prof_dir.is_dir()}
        if not prof_dir.is_dir():
            return info
        total_size = 0
        file_count = 0
        dir_count = 0
        for root, dirs, files in os.walk(prof_dir):
            dir_count += len(dirs)
            file_count += len(files)
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total_size += os.path.getsize(fp)
                except OSError:
                    pass
        info["size"] = total_size
        info["size_human"] = ProfileManager._format_size(total_size)
        info["files"] = file_count
        info["directories"] = dir_count
        config_file = prof_dir / "config.yaml"
        if config_file.exists():
            info["config_size"] = config_file.stat().st_size
        env_file = prof_dir / ".env"
        if env_file.exists():
            info["env_size"] = env_file.stat().st_size
        sessions_dir = prof_dir / "sessions"
        info["session_count"] = len(list(sessions_dir.iterdir())) if sessions_dir.is_dir() else 0
        skills_dir = prof_dir / "skills"
        info["skills"] = [p.name for p in skills_dir.iterdir() if p.suffix == ".py"] if skills_dir.is_dir() else []
        info["created"] = datetime.fromtimestamp(prof_dir.stat().st_ctime).isoformat()
        info["modified"] = datetime.fromtimestamp(prof_dir.stat().st_mtime).isoformat()
        return info

    @staticmethod
    def _apply_profile_env(name: str) -> None:
        env_file = _get_profile_dir(name) / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ[f"LAAP_PROFILE_{k}"] = v
        os.environ["LAAP_PROFILE"] = name
        os.environ["LAAP_HOME"] = str(_get_profile_dir(name))

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


# ── Singleton ──────────────────────────────────────────────────────────

profile_manager = ProfileManager()
