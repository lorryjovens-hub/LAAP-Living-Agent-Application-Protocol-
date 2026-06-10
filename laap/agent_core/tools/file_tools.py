"""File Tools — 文件系统操作工具"""
from __future__ import annotations
import os, json, shutil, glob, logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent_core.tools.file")

def search_files(pattern: str, path: str = ".") -> str:
    """搜索匹配的文件"""
    try:
        matches = []
        for root, dirs, files in os.walk(path):
            for f in files:
                if pattern.lower() in f.lower():
                    matches.append(os.path.join(root, f))
            if len(matches) > 100:
                break
        return json.dumps({"matches": matches[:100], "total": len(matches)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

def file_info(path: str) -> str:
    """获取文件信息"""
    try:
        stat = os.stat(path)
        return json.dumps({
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
            "is_dir": os.path.isdir(path),
            "is_file": os.path.isfile(path),
            "ext": os.path.splitext(path)[1],
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

def copy_file(src: str, dst: str) -> str:
    """复制文件"""
    try:
        shutil.copy2(src, dst)
        return json.dumps({"success": True, "from": src, "to": dst})
    except Exception as e:
        return json.dumps({"error": str(e)})

def move_file(src: str, dst: str) -> str:
    """移动文件"""
    try:
        shutil.move(src, dst)
        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})

def delete_file(path: str) -> str:
    """删除文件"""
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})

def mkdir(path: str) -> str:
    """创建目录"""
    try:
        os.makedirs(path, exist_ok=True)
        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})

def tree_view(path: str = ".", max_depth: int = 2) -> str:
    """树形查看目录"""
    lines = []
    def _walk(dir_path, depth):
        if depth > max_depth:
            return
        try:
            for item in sorted(os.listdir(dir_path)):
                full = os.path.join(dir_path, item)
                prefix = "  " * depth + ("└─ " if depth > 0 else "")
                lines.append(f"{prefix}{item}")
                if os.path.isdir(full):
                    _walk(full, depth + 1)
        except PermissionError:
            lines.append("  " * depth + "└─ [权限不足]")
    _walk(path, 0)
    return "\n".join(lines[:100])

def grep(pattern: str, path: str = ".", file_glob: str = "*.py") -> str:
    """在文件中搜索文本"""
    import re
    results = []
    try:
        for root, dirs, files in os.walk(path):
            for f in files:
                if not glob.fnmatch.fnmatch(f, file_glob):
                    continue
                fp = os.path.join(root, f)
                try:
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as fh:
                        for i, line in enumerate(fh, 1):
                            if pattern in line:
                                results.append(f"{fp}:{i}: {line.rstrip()[:100]}")
                                if len(results) >= 50:
                                    break
                except:
                    pass
                if len(results) >= 50:
                    break
    except Exception as e:
        return json.dumps({"error": str(e)})
    return json.dumps({"matches": results[:50], "total": len(results)}, ensure_ascii=False)

TOOL_DEFS = [
    {"name":"search_files","fn":search_files,"desc":"搜索文件","params":{"pattern":{"type":"string"},"path":{"type":"string"}},"req":["pattern"]},
    {"name":"file_info","fn":file_info,"desc":"获取文件信息","params":{"path":{"type":"string"}},"req":["path"]},
    {"name":"copy_file","fn":copy_file,"desc":"复制文件","params":{"src":{"type":"string"},"dst":{"type":"string"}},"req":["src","dst"]},
    {"name":"move_file","fn":move_file,"desc":"移动文件","params":{"src":{"type":"string"},"dst":{"type":"string"}},"req":["src","dst"]},
    {"name":"delete_file","fn":delete_file,"desc":"删除文件","params":{"path":{"type":"string"}},"req":["path"]},
    {"name":"mkdir","fn":mkdir,"desc":"创建目录","params":{"path":{"type":"string"}},"req":["path"]},
    {"name":"tree_view","fn":tree_view,"desc":"树形查看目录","params":{"path":{"type":"string"},"max_depth":{"type":"integer"}}},
    {"name":"grep","fn":grep,"desc":"搜索文件内容","params":{"pattern":{"type":"string"},"path":{"type":"string"},"file_glob":{"type":"string"}},"req":["pattern"]},
]
