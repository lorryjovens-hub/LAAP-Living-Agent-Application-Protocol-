"""
LAAP — Production Code Search
grep/ripgrep-based code search with semantic awareness.
"""

from __future__ import annotations
import os, re, subprocess, logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("laap.editor.search")


class CodeSearch:
    """Enterprise-grade code search. Uses ripgrep when available, falls back to Python."""

    MAX_RESULTS = 50

    @staticmethod
    def grep(pattern: str, path: str = ".", glob: Optional[str] = None,
             max_results: int = 50, context_lines: int = 2,
             case_sensitive: bool = False, regex: bool = True) -> Dict[str, Any]:
        """Search for pattern in files. Uses ripgrep for speed.

        Args:
            pattern: Search pattern (regex by default)
            path: Search root
            glob: File filter (e.g. "*.py")
            max_results: Max matches
            context_lines: Lines of context before/after match
            case_sensitive: Case sensitive search
            regex: Treat pattern as regex (False = plain text)

        Returns:
            Dict with results grouped by file
        """
        root = Path(path).resolve()
        if not root.exists():
            return {"success": False, "error": f"Path not found: {path}"}

        max_results = min(max_results, CodeSearch.MAX_RESULTS)
        results = []
        match_count = 0

        # Try ripgrep first (much faster)
        rg_available = CodeSearch._check_rg_available()
        if rg_available:
            try:
                cmd = ["rg", "-n", "--with-filename", "--color=never"]
                if context_lines > 0:
                    cmd.extend(["-C", str(context_lines)])
                if not case_sensitive:
                    cmd.append("-i")
                if glob:
                    cmd.extend(["-g", glob])
                cmd.extend(["--max-count", str(max_results * 2)])
                if not regex:
                    cmd.append("-F")
                cmd.extend([pattern, str(root)])

                rg_result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if rg_result.returncode == 0 or rg_result.returncode == 1:
                    output = rg_result.stdout
                    # Parse rg output
                    current_file = None
                    current_lines = []
                    for line in output.split("\n"):
                        if line.startswith("--"):
                            continue
                        if line.strip() and ": " not in line[:30] and not line.startswith(" "):
                            current_file = line
                            continue
                        match_count += 1
                        if match_count <= max_results:
                            results.append(line)
                        if match_count > max_results:
                            break

                    return {
                        "success": True,
                        "pattern": pattern,
                        "engine": "ripgrep",
                        "results": results[:max_results],
                        "total_matches": match_count,
                        "truncated": match_count > max_results,
                        "path": str(root),
                    }
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        # Pure Python fallback
        glob_pattern = glob if glob else "*"
        try:
            import fnmatch
            matched_files = []
            for f in root.rglob("*"):
                if f.is_file() and fnmatch.fnmatch(f.name, glob_pattern):
                    if not any(p.startswith(".") for p in f.parts):
                        try:
                            text = f.read_text(encoding="utf-8", errors="replace")
                            matches = CodeSearch._search_text(text, pattern, case_sensitive, regex)
                            if matches:
                                matched_files.append((f, text, matches))
                        except Exception:
                            continue

            for file_path, text, matches in matched_files:
                for line_num, line, ctx_before, ctx_after in matches[:20]:
                    rel_path = file_path.relative_to(root)
                    highlight = f"{rel_path}:{line_num}: {line.strip()}"
                    if context_lines > 0:
                        if ctx_before:
                            for cl in ctx_before:
                                results.append(f"  {cl}")
                        results.append(f"> {highlight}")
                        if ctx_after:
                            for cl in ctx_after:
                                results.append(f"  {cl}")
                    else:
                        results.append(highlight)
                    match_count += 1
                    if match_count >= max_results:
                        break
                if match_count >= max_results:
                    break
        except Exception as e:
            return {"success": False, "error": f"Search error: {e}"}

        return {
            "success": True,
            "pattern": pattern,
            "engine": "python",
            "results": results[:max_results],
            "total_matches": match_count,
            "truncated": match_count > max_results,
            "path": str(root),
        }

    @staticmethod
    def _search_text(text: str, pattern: str, case_sensitive: bool, regex: bool) -> List[tuple]:
        """Search a single text string for pattern."""
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            if regex:
                matches = list(re.finditer(pattern, text, flags))
            else:
                if case_sensitive:
                    matches = [(m.start(), m.end()) for m in re.finditer(re.escape(pattern), text)]
                else:
                    matches = [(m.start(), m.end()) for m in re.finditer(re.escape(pattern), text, re.IGNORECASE)]
        except re.error:
            return []

        lines = text.split("\n")
        results = []
        for match in matches:
            if isinstance(match, re.Match):
                start_pos = match.start()
            else:
                start_pos = match[0]

            line_num = text[:start_pos].count("\n") + 1
            line_start = text.rfind("\n", 0, start_pos) + 1
            line_end = text.find("\n", start_pos)
            if line_end == -1:
                line_end = len(text)
            line = text[line_start:line_end]

            context_before = []
            context_after = []
            for i in range(max(0, line_num - 3), line_num):
                if i < len(lines):
                    context_before.append(f"{i + 1}: {lines[i].strip()}")
            for i in range(line_num, min(len(lines), line_num + 3)):
                if i < len(lines) and i != line_num - 1:
                    context_after.append(f"{i + 1}: {lines[i].strip()}")

            results.append((line_num, line, context_before, context_after))
        return results

    @staticmethod
    def find_files(pattern: str, path: str = ".", max_results: int = 50) -> Dict[str, Any]:
        """Find files matching a glob pattern.

        Args:
            pattern: Glob pattern like "**/*.py" or "src/**/*.ts"
            path: Root directory
            max_results: Max results

        Returns:
            Dict with matching file paths
        """
        root = Path(path).resolve()
        if not root.exists():
            return {"success": False, "error": f"Path not found: {path}"}

        results = []
        try:
            for f in root.glob(pattern):
                if f.is_file():
                    rel = f.relative_to(root)
                    size = f.stat().st_size
                    results.append({"path": str(rel), "size": size})
                    if len(results) >= max_results:
                        break
        except Exception as e:
            return {"success": False, "error": f"Glob error: {e}"}

        return {"success": True, "pattern": pattern, "results": results, "total": len(results)}

    @staticmethod
    def find_symbols(query: str, path: str = ".") -> Dict[str, Any]:
        """Find function/class definitions matching a query.

        Uses regex to identify function/class definitions across known languages.
        """
        # Patterns for common languages
        patterns = [
            (r"(?:async\s+)?(?:def|class)\s+(\w*{0}\w*)", ["python"]),
            (r"(?:export\s+)?(?:function|class|const|let|var)\s+(\w*{0}\w*)", ["javascript", "typescript"]),
            (r"(?:pub\s+)?(?:fn|struct|enum|trait|impl|mod)\s+(\w*{0}\w*)", ["rust"]),
            (r"(?:func|type|struct)\s+(\w*{0}\w*)", ["go"]),
            (r"(?:public|private|protected)?\s*(?:function|class|interface)\s+(\w*{0}\w*)", ["java", "php"]),
        ]

        results = []
        escaped = re.escape(query)
        for base_pattern, languages in patterns:
            pattern = base_pattern.format(escaped)
            try:
                search_result = CodeSearch.grep(pattern, path, max_results=30)
                if search_result.get("success"):
                    for line in search_result.get("results", []):
                        items = line.split(": ", 2)
                        if len(items) >= 2:
                            results.append({
                                "file": items[0],
                                "line": items[1] if len(items) > 1 else "",
                                "languages": languages,
                            })
            except Exception:
                continue

        return {"success": True, "query": query, "symbols": results[:30], "total": len(results)}

    @staticmethod
    def _check_rg_available() -> bool:
        """Check if ripgrep is installed."""
        try:
            result = subprocess.run(["rg", "--version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False


code_search = CodeSearch()
