"""
LAAP — Production File Operations
Claude Code-grade file system manipulation: read, write, edit, patch, create, delete.
"""

from __future__ import annotations
import os, difflib, logging, re, fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from laap.editor.path_scope import path_scope as _psc

logger = logging.getLogger("laap.editor.files")


class FileSystem:
    """Low-level filesystem operations with safety checks."""

    MAX_FILE_SIZE = 10 * 1024 * 1024
    MAX_SEARCH_RESULTS = 100

    READ_CHUNK_LINES = 2000
    PROJECT_FILE_PATTERNS = {
        "python": ["*.py", "setup.py", "pyproject.toml", "requirements.txt", "Pipfile"],
        "node": ["*.js", "*.jsx", "*.ts", "*.tsx", "package.json", "tsconfig.json"],
        "rust": ["*.rs", "Cargo.toml", "Cargo.lock"],
        "go": ["*.go", "go.mod", "go.sum"],
        "java": ["*.java", "pom.xml", "build.gradle"],
    }

    @staticmethod
    def read(file_path: str, offset: int = 0, limit: Optional[int] = None) -> Dict[str, Any]:
        try:
            _psc.restrict(file_path)
        except PermissionError as e:
            return {"success": False, "error": f"Path blocked: {e}"}
        path = Path(file_path).resolve()
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        if not path.is_file() or path.is_symlink() and not path.exists():
            return {"success": False, "error": f"Not a regular file: {file_path}"}

        file_size = path.stat().st_size
        if file_size > FileSystem.MAX_FILE_SIZE:
            return {"success": False, "error": f"File too large ({file_size / 1024 / 1024:.1f}MB)"}

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"success": False, "error": f"Cannot read file: {e}"}

        lines = text.split("\n")
        total_lines = len(lines)
        start = max(0, offset)
        end = min(total_lines, start + limit) if limit else total_lines
        result_lines = []
        for i in range(start, end):
            result_lines.append(f"{i + 1:>6} | {lines[i]}")

        return {
            "success": True,
            "path": str(path),
            "content": "\n".join(result_lines),
            "total_lines": total_lines,
            "file_size": file_size,
            "language": path.suffix.lstrip("."),
            "start_line": start + 1,
            "end_line": end,
            "raw_content": text if file_size < 1024 * 1024 else None,
        }

    @staticmethod
    def write(file_path: str, content: str, create_dirs: bool = True) -> Dict[str, Any]:
        try:
            _psc.restrict(file_path)
        except PermissionError as e:
            return {"success": False, "error": f"Path blocked: {e}"}
        path = Path(file_path).resolve()
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(content, encoding="utf-8")
            lines = content.count("\n") + 1 if content else 0
            return {"success": True, "path": str(path), "lines": lines, "size": len(content.encode("utf-8"))}
        except Exception as e:
            return {"success": False, "error": f"Cannot write file: {e}"}

    @staticmethod
    def edit(file_path: str, old_string: str, new_string: str,
             replace_all: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        try:
            _psc.restrict(file_path)
        except PermissionError as e:
            return {"success": False, "error": f"Path blocked: {e}"}
        path = Path(file_path).resolve()
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        original = path.read_text(encoding="utf-8")
        count = original.count(old_string)

        if count == 0:
            return {"success": False, "error": f"Old string not found in file. It appears {count} times. "
                                                "Try using a more unique match or check exact whitespace."}
        if count > 1 and not replace_all:
            return {"success": False, "error": f"Old string found {count} times. Use replace_all=True "
                                                "or provide a more specific match."}

        new_content = original.replace(old_string, new_string, 1) if not replace_all else original.replace(old_string, new_string)

        if dry_run:
            diff = list(difflib.unified_diff(
                original.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{path.name}", tofile=f"b/{path.name}",
            ))
            return {"success": True, "dry_run": True, "diff": "".join(diff), "changes": count}

        try:
            new_content.encode("utf-8")
        except UnicodeEncodeError:
            return {"success": False, "error": "New string produces invalid UTF-8"}

        path.write_text(new_content, encoding="utf-8")

        diff = list(difflib.unified_diff(
            original.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{path.name}", tofile=f"b/{path.name}",
        ))
        return {"success": True, "diff": "".join(diff)[:10000], "changes": count, "path": str(path)}

    @staticmethod
    def patch(file_path: str, diff_content: str) -> Dict[str, Any]:
        path = Path(file_path).resolve()
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        original = path.read_text(encoding="utf-8")
        try:
            patch_set = difflib.patch(original, diff_content.splitlines(keepends=True))
            patched = "".join(patch_set)
        except Exception as e:
            return {"success": False, "error": f"Patch apply failed: {e}"}
        if patched == original:
            return {"success": False, "error": "Patch did not change the file"}
        path.write_text(patched, encoding="utf-8")
        return {"success": True, "path": str(path)}

    @staticmethod
    def delete(file_path: str, safe: bool = True) -> Dict[str, Any]:
        try:
            _psc.restrict(file_path)
        except PermissionError as e:
            return {"success": False, "error": f"Path blocked: {e}"}
        path = Path(file_path).resolve()
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        if safe and not path.is_relative_to(Path.cwd()):
            return {"success": False, "error": "Cannot delete files outside working directory in safe mode"}
        try:
            path.unlink()
            return {"success": True, "path": str(path)}
        except Exception as e:
            return {"success": False, "error": f"Cannot delete: {e}"}

    @staticmethod
    def tree(dir_path: str = ".", max_depth: int = 3, show_hidden: bool = False,
             max_files: int = 200) -> Dict[str, Any]:
        root = Path(dir_path).resolve()
        if not root.exists():
            return {"success": False, "error": f"Directory not found: {dir_path}"}
        skip_dirs = {"node_modules", ".git", "__pycache__", ".venv", "venv", "target",
                     ".next", ".turbo", "dist", "build", ".svelte-kit", ".cache",
                     ".mypy_cache", ".pytest_cache", ".ruff_cache", ".DS_Store"}
        skip_ext = {".pyc", ".pyo", ".so", ".o", ".class", ".jar"} if not show_hidden else set()
        items = []
        count = [0]

        def _walk(directory: Path, depth: int):
            if depth > max_depth or count[0] >= max_files:
                return
            try:
                entries = sorted(directory.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
            except PermissionError:
                return
            for entry in entries:
                if entry.name in skip_dirs: continue
                if not show_hidden and entry.name.startswith("."): continue
                if entry.suffix in skip_ext: continue
                if count[0] >= max_files: return
                count[0] += 1
                indent = "  " * depth
                if entry.is_dir():
                    items.append(f"{indent}{entry.name}/")
                    _walk(entry, depth + 1)
                else:
                    size = entry.stat().st_size
                    size_str = f"{size:,}B" if size < 1024 else f"{size/1024:.1f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
                    items.append(f"{indent}{entry.name} ({size_str})")
        _walk(root, 0)
        return {"success": True, "root": str(root), "tree": "\n".join(items),
                "total_entries": count[0], "depth": max_depth}

    @staticmethod
    def detect_project_type(dir_path: str = ".") -> Dict[str, Any]:
        root = Path(dir_path).resolve()
        result = {"success": True, "root": str(root), "languages": set(),
                  "frameworks": [], "package_managers": [], "dependencies": [],
                  "project_type": "unknown"}
        checks = {
            "package.json": lambda: FileSystem._read_json(root / "package.json"),
            "pyproject.toml": lambda: (root / "pyproject.toml").exists(),
            "setup.py": lambda: (root / "setup.py").exists(),
            "requirements.txt": lambda: (root / "requirements.txt").exists(),
            "Cargo.toml": lambda: (root / "Cargo.toml").exists(),
            "go.mod": lambda: (root / "go.mod").exists(),
            "tsconfig.json": lambda: (root / "tsconfig.json").exists(),
            "Makefile": lambda: (root / "Makefile").exists(),
            "Dockerfile": lambda: (root / "Dockerfile").exists(),
            ".github/workflows": lambda: (root / ".github" / "workflows").exists(),
        }
        for name, check_fn in checks.items():
            try:
                if check_fn(): result["frameworks"].append(name)
            except Exception: pass
        lang_extensions = {
            "python": {".py", ".pyi", ".pyx"}, "typescript": {".ts", ".tsx"},
            "javascript": {".js", ".jsx", ".mjs"}, "rust": {".rs"}, "go": {".go"},
            "java": {".java", ".kt", ".kts"}, "cpp": {".cpp", ".hpp", ".cc", ".h"},
            "css": {".css", ".scss", ".less", ".sass"}, "html": {".html", ".htm"},
            "json/yaml": {".json", ".yaml", ".yml"}, "shell": {".sh", ".bash", ".zsh"},
            "sql": {".sql"}, "ruby": {".rb"}, "php": {".php"},
        }
        for lang, exts in lang_extensions.items():
            cnt = 0
            for f in root.rglob("*"):
                if f.suffix in exts and not any(p.startswith(".") for p in f.parts):
                    cnt += 1
                    if cnt >= 3: result["languages"].add(lang); break
        if "python" in result["languages"]: result["project_type"] = "python"
        elif "typescript" in result["languages"] or "javascript" in result["languages"]: result["project_type"] = "node"
        elif "rust" in result["languages"]: result["project_type"] = "rust"
        elif "go" in result["languages"]: result["project_type"] = "go"
        result["languages"] = list(result["languages"])
        return result

    @staticmethod
    def _read_json(path: Path) -> Optional[Dict]:
        try: import json; return json.loads(path.read_text(encoding="utf-8"))
        except Exception: return None

    @staticmethod
    def create_project_structure(structure: Dict[str, Any], base_path: str = ".") -> List[str]:
        base = Path(base_path).resolve()
        created = []
        for dir_path in structure.get("dirs", []):
            full = base / dir_path
            full.mkdir(parents=True, exist_ok=True)
            created.append(str(full))
        for file_path, content in structure.get("files", {}).items():
            full = base / file_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
            created.append(str(full))
        return created


file_system = FileSystem()
