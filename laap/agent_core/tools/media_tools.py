"""Media Tools — 媒体处理工具"""
from __future__ import annotations
import json, base64, logging, os, time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent_core.tools.media")

def encode_image(path: str) -> str:
    """将图片编码为base64"""
    try:
        with open(path, 'rb') as f:
            data = base64.b64encode(f.read()).decode()
        return json.dumps({"format": "base64", "size": len(data), "data": data[:100] + "..."})
    except Exception as e:
        return json.dumps({"error": str(e)})

def image_info(path: str) -> str:
    """获取图片信息"""
    try:
        size = os.path.getsize(path)
        return json.dumps({"path": path, "size_bytes": size, "size_kb": round(size/1024, 1)})
    except Exception as e:
        return json.dumps({"error": str(e)})

TOOL_DEFS = [
    {"name":"encode_image","fn":encode_image,"desc":"编码图片为base64","params":{"path":{"type":"string"}},"req":["path"]},
    {"name":"image_info","fn":image_info,"desc":"获取图片信息","params":{"path":{"type":"string"}},"req":["path"]},
]
