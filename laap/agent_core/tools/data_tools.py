"""Data Tools — 数据处理工具"""
from __future__ import annotations
import json, csv, io, logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent_core.tools.data")

def json_read(path: str) -> str:
    """读取JSON文件"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return json.dumps(data, ensure_ascii=False, default=str)[:3000]
    except Exception as e:
        return json.dumps({"error": str(e)})

def json_write(path: str, data: Any) -> str:
    """写入JSON文件"""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return json.dumps({"success": True, "path": path})
    except Exception as e:
        return json.dumps({"error": str(e)})

def csv_read(path: str, limit: int = 50) -> str:
    """读取CSV文件"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = []
            for i, row in enumerate(reader):
                if i >= limit:
                    break
                rows.append(row)
        return json.dumps({"columns": list(rows[0].keys()) if rows else [], "rows": rows[:limit], "total": len(rows)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

TOOL_DEFS = [
    {"name":"json_read","fn":json_read,"desc":"读取JSON","params":{"path":{"type":"string"}},"req":["path"]},
    {"name":"json_write","fn":json_write,"desc":"写入JSON","params":{"path":{"type":"string"},"data":{"type":"object"}},"req":["path","data"]},
    {"name":"csv_read","fn":csv_read,"desc":"读取CSV","params":{"path":{"type":"string"},"limit":{"type":"integer"}},"req":["path"]},
]
