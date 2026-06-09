"""
LAAP — Production Code Editing Tools
Claude Code-grade file operations: read, write, edit (exact replace), search, project awareness.
"""

from __future__ import annotations
import json, logging

from laap.editor.operations.files import file_system
from laap.editor.search.search import code_search
from laap.git.operations import git
from laap.shell.executor import shell

logger = logging.getLogger("laap.tools.code_edit")


def register_all(registry):
    """注册所有代码编辑工具 - 幂等安全，可被多次调用"""
    # 使用 registry.register 的幂等性来避免重复
    _tools_registered = getattr(registry, '_code_tools_registered', False)
    if _tools_registered:
        return
    registry._code_tools_registered = True

    @registry.tool(name="read_file", category="code",
                   description="Read file contents with line numbers. View source code, configs, logs.")
    def read_file(file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """Read a file with line-numbered output.

        Args:
            file_path: Absolute or relative path to the file
            offset: Starting line (0-indexed, default 0)
            limit: Max lines to return (default 2000)
        """
        result = file_system.read(file_path, offset, limit)
        if not result["success"]:
            return json.dumps({"error": result["error"]})
        info = f"File: {result['path']} ({result['total_lines']} lines, {result['language']})"
        return json.dumps({"success": True, "path": result["path"],
                           "content": result["content"], "total_lines": result["total_lines"],
                           "language": result["language"], "info": info})

    @registry.tool(name="write_file", category="code",
                   description="Create or overwrite a file with full content.")
    def write_file(file_path: str, content: str) -> str:
        """Write content to a file (creates directories if needed).

        Args:
            file_path: Absolute path to write
            content: Full file content
        """
        result = file_system.write(file_path, content)
        if not result["success"]:
            return json.dumps({"error": result["error"]})
        return json.dumps({"success": True, "path": result["path"],
                           "lines": result["lines"], "size": result["size"]})

    @registry.tool(name="edit_file", category="code",
                   description="Edit a file via EXACT string replacement. Like Claude Code's edit tool.")
    def edit_file(file_path: str, old_string: str, new_string: str,
                  replace_all: bool = False, dry_run: bool = False) -> str:
        """Edit a file by finding old_string and replacing with new_string.
        IMPORTANT: old_string must match exactly, including whitespace and indentation.

        Args:
            file_path: File to edit
            old_string: Text to find (must match EXACTLY including whitespace)
            new_string: Replacement text
            replace_all: Replace ALL occurrences (default: only first)
            dry_run: Preview diff without applying
        """
        result = file_system.edit(file_path, old_string, new_string, replace_all, dry_run)
        if not result["success"]:
            return json.dumps({"error": result["error"]})
        return json.dumps({"success": True, "diff": result.get("diff", ""),
                           "changes": result.get("changes", 0), "path": result.get("path", "")})

    @registry.tool(name="create_file", category="code",
                   description="Create a new file with content. Creates parent directories.")
    def create_file(file_path: str, content: str = "") -> str:
        """Create a new file.

        Args:
            file_path: Path for the new file
            content: Initial file content (optional)
        """
        result = file_system.write(file_path, content)
        return json.dumps(result)

    @registry.tool(name="list_dir", category="code",
                   description="List directory contents with a file tree view. Understands project structure.")
    def list_dir(path: str = ".", depth: int = 3, max_files: int = 200) -> str:
        """Display directory tree.

        Args:
            path: Directory path
            depth: Max recursion depth (default 3)
            max_files: Max total entries
        """
        result = file_system.tree(path, depth, max_files=max_files)
        if not result["success"]:
            return json.dumps({"error": result["error"]})
        return json.dumps({"success": True, "root": result["root"],
                           "tree": result["tree"], "total": result["total_entries"]})

    @registry.tool(name="search_code", category="code",
                   description="Search for code across the project. Uses ripgrep when available.")
    def search_code(pattern: str, path: str = ".", glob: str = "",
                    max_results: int = 30, context: int = 2) -> str:
        """Search codebase with regex pattern.

        Args:
            pattern: Search pattern (regex supported)
            path: Root search directory
            glob: File filter, e.g. "*.py" or "*.tsx"
            max_results: Max matches to return
            context: Lines of context before/after match
        """
        result = code_search.grep(pattern, path, glob or None, max_results, context)
        if not result["success"]:
            return json.dumps({"error": result["error"]})
        return json.dumps({"success": True, "engine": result.get("engine", "python"),
                           "results": result.get("results", []), "total": result.get("total_matches", 0),
                           "truncated": result.get("truncated", False)})

    @registry.tool(name="find_files", category="code",
                   description="Find files matching a glob pattern.")
    def find_files(pattern: str, path: str = ".") -> str:
        """Find files by glob pattern.

        Args:
            pattern: Glob pattern, e.g. "**/*.py" or "src/**/*.ts"
            path: Search root
        """
        result = code_search.find_files(pattern, path)
        return json.dumps(result)

    @registry.tool(name="project_info", category="code",
                   description="Detect project type, language, framework, and dependencies.")
    def project_info(path: str = ".") -> str:
        """Analyze project structure and detect technologies.

        Args:
            path: Project root directory
        """
        result = file_system.detect_project_type(path)
        return json.dumps(result)

    @registry.tool(name="grep", category="code",
                   description="Quick grep search across the codebase (alias for search_code).")
    def grep(pattern: str, path: str = ".", glob: str = "") -> str:
        return search_code(pattern, path, glob)

    @registry.tool(name="diff_file", category="code",
                   description="Show diff of current changes or between files.")
    def diff_file(target_a: str = ".", target_b: str = "") -> str:
        """Show diff (git diff or file comparison).

        Args:
            target_a: File path or directory (default: current dir for git diff)
            target_b: Optional second file for comparison
        """
        if target_b:
            result = file_system.edit(target_a, "", "", dry_run=True)
            if "diff" in result:
                return json.dumps({"success": True, "diff": result["diff"]})
        # Fall back to git diff
        try:
            result = git.diff(target_a if not target_b else ".")
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
