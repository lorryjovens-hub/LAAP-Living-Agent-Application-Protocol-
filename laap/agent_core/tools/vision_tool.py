"""Vision Tool — 图像分析与OCR"""
from __future__ import annotations
import json, base64, logging, os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent_core.tools.vision")

class VisionTool:
    def analyze_image(self, image_path: str, prompt: str = "描述这个图片") -> str:
        """分析图像内容"""
        try:
            if not os.path.exists(image_path):
                return json.dumps({"error": f"File not found: {image_path}"})
            with open(image_path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode()
            return json.dumps({"image": image_path, "size": len(b64),
                              "hint": f"图片已编码({len(b64)}b)，需LLM视觉能力分析"})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def image_info(self, image_path: str) -> str:
        """获取图片信息"""
        try:
            stat = os.stat(image_path)
            return json.dumps({"path": image_path, "bytes": stat.st_size,
                              "modified": stat.st_mtime})
        except Exception as e:
            return json.dumps({"error": str(e)})

TOOL_DEFS = [
    {"name":"analyze_image","fn":VisionTool().analyze_image,"desc":"分析图像","params":{"image_path":{"type":"string"},"prompt":{"type":"string"}},"req":["image_path"]},
    {"name":"image_info","fn":VisionTool().image_info,"desc":"图片信息","params":{"image_path":{"type":"string"}},"req":["image_path"]},
]
