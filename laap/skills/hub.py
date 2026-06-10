"""LAAP — Skills Hub: GitHub skill discovery and installation.

Discovers skills from GitHub repositories, installs them locally,
and manages the skill lifecycle.
"""

from __future__ import annotations
import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from laap.skills.engine import SkillEngine, Skill

logger = logging.getLogger("laap.skills.hub")

# Default skill registries (GitHub repos with LAAP skills)
DEFAULT_REGISTRIES = [
    {
        "name": "LAAP Official",
        "url": "https://api.github.com/repos/laap-agi/laap-skills/contents/skills",
        "type": "github",
    },
    {
        "name": "Community",
        "url": "https://api.github.com/search/repositories?q=laap-skill&sort=updated",
        "type": "github-search",
    },
]

SKILLS_DIR = Path.home() / ".laap" / "skills"
HUB_INDEX = SKILLS_DIR / "hub_index.json"


def _ensure_skills_dir() -> Path:
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    return SKILLS_DIR


# ── Remote Discovery ─────────────────────────────────────────

def fetch_registry(url: str, timeout: int = 15) -> Optional[List[Dict]]:
    """Fetch skill listing from a GitHub API URL."""
    try:
        import httpx
        headers = {"Accept": "application/vnd.github.v3+json"}
        resp = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
        if resp.status_code == 200:
            return resp.json()
        logger.warning(f"Registry fetch failed ({resp.status_code}): {url}")
    except ImportError:
        logger.error("pip install httpx for skill hub support")
    except Exception as e:
        logger.warning(f"Registry fetch error: {e}")
    return None


def discover_remote_skills() -> List[Dict]:
    """Discover available skills from all registries.

    Returns list of skill metadata dicts with keys:
        name, description, author, repo, url, tags, version
    """
    skills = []
    for registry in DEFAULT_REGISTRIES:
        data = fetch_registry(registry["url"])
        if not data:
            continue

        if registry["type"] == "github":
            for item in data if isinstance(data, list) else []:
                name = item.get("name", "").replace(".md", "").replace("-", " ").title()
                skills.append({
                    "name": name,
                    "description": f"Skill from {registry['name']}",
                    "author": registry["name"],
                    "repo": registry["url"].split("/contents")[0],
                    "url": item.get("download_url", ""),
                    "tags": ["community"],
                    "version": "1.0.0",
                })

        elif registry["type"] == "github-search":
            items = data.get("items", [])
            for repo in items[:20]:
                skills.append({
                    "name": repo.get("name", "").replace("laap-skill-", "").replace("-", " ").title(),
                    "description": repo.get("description", "") or "No description",
                    "author": repo.get("owner", {}).get("login", "unknown"),
                    "repo": repo.get("html_url", ""),
                    "url": repo.get("clone_url", ""),
                    "tags": ["github", "community"],
                    "version": "1.0.0",
                    "stars": repo.get("stargazers_count", 0),
                })

    # Cache to local index
    _ensure_skills_dir()
    try:
        HUB_INDEX.write_text(json.dumps(skills, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass

    return skills


def get_cached_skills() -> List[Dict]:
    """Get cached skill index (no network)."""
    if HUB_INDEX.exists():
        try:
            return json.loads(HUB_INDEX.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return []


# ── Installation ──────────────────────────────────────────────

def install_skill(skill_info: Dict, target_name: Optional[str] = None) -> Tuple[bool, str]:
    """Install a skill from the hub.

    Args:
        skill_info: Skill metadata dict from discover_remote_skills()
        target_name: Optional custom name for the installed skill

    Returns:
        (success, message)
    """
    name = target_name or skill_info.get("name", "unknown")
    url = skill_info.get("url", "")
    repo = skill_info.get("repo", "")

    if not url and not repo:
        return False, "No download URL provided"

    target_dir = _ensure_skills_dir() / _slugify(name)
    target_dir.mkdir(parents=True, exist_ok=True)

    # Try direct file download first
    if url and url.endswith(".md"):
        try:
            import httpx
            resp = httpx.get(url, timeout=15)
            if resp.status_code == 200:
                (target_dir / "SKILL.md").write_text(resp.text, encoding="utf-8")
                return True, f"Installed '{name}' from URL"
        except Exception as e:
            logger.warning(f"URL download failed: {e}")

    # Try git clone
    if repo:
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo, str(target_dir / "_repo")],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                repo_dir = target_dir / "_repo"
                # Find SKILL.md
                for md in repo_dir.rglob("SKILL.md"):
                    shutil.copy2(str(md), str(target_dir / "SKILL.md"))
                    break
                # Copy linked files
                for f in repo_dir.iterdir():
                    if f.name != "SKILL.md" and f.is_file():
                        shutil.copy2(str(f), str(target_dir / f.name))
                # Cleanup
                shutil.rmtree(repo_dir, ignore_errors=True)
                return True, f"Installed '{name}' from {repo}"
            else:
                return False, f"Git clone failed: {result.stderr[:200]}"
        except FileNotFoundError:
            return False, "git not found on PATH"
        except subprocess.TimeoutExpired:
            return False, "Git clone timed out"

    return False, "No installable source found"


def uninstall_skill(name: str) -> Tuple[bool, str]:
    """Remove an installed skill."""
    target = _ensure_skills_dir() / _slugify(name)
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
        return True, f"Uninstalled '{name}'"
    return False, f"Skill '{name}' not found"


def list_installed_skills() -> List[Dict]:
    """List locally installed skills."""
    engine = SkillEngine([_ensure_skills_dir()])
    engine.discover()
    return [s.to_dict() for s in engine.get_all()]


def _slugify(name: str) -> str:
    import re
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    return re.sub(r"-+", "-", name).strip("-")

    def search(self, query: str) -> List[SkillMeta]:
        q = query.lower()
        return [m for m in self._skills.values() if q in m.name.lower() or q in m.description.lower()]
    
    def by_category(self, category: str) -> List[SkillMeta]:
        return [m for m in self._skills.values() if m.category == category]
    
    def remove(self, name: str) -> bool:
        if name in self._loaded:
            del self._loaded[name]
        if name in self._skills:
            del self._skills[name]
            return True
        return False
