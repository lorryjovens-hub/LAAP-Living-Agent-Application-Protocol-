"""Computer Use Tool — 屏幕操作(截图/鼠标/键盘)"""
from __future__ import annotations
import time, json, logging, os, struct, io
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("agent_core.tools.computer")

class ComputerUseTool:
    """计算机使用 — 屏幕截图分析、鼠标点击、键盘输入、滚动"""
    
    def __init__(self):
        self._screen_size = (1920, 1080)
        self._safe_zone = True
    
    def screenshot(self) -> str:
        """截取屏幕截图(base64)"""
        try:
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                img = sct.grab(monitor)
                import base64
                from PIL import Image
                pil_img = Image.frombytes("RGB", img.size, img.rgb)
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode()
                return json.dumps({"width": img.size[0], "height": img.size[1], "data": b64[:50]+"..."})
        except ImportError:
            return json.dumps({"error": "mss/PIL not installed", "hint": "pip install mss Pillow"})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def mouse_click(self, x: int, y: int, button: str = "left") -> str:
        """鼠标点击指定坐标"""
        try:
            import pyautogui
            pyautogui.click(x, y, button=button)
            return json.dumps({"success": True, "x": x, "y": y})
        except ImportError:
            return json.dumps({"error": "pyautogui not installed"})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def type_text(self, text: str) -> str:
        """键盘输入文本"""
        try:
            import pyautogui
            pyautogui.write(text, interval=0.05)
            return json.dumps({"success": True, "text": text[:50]})
        except ImportError:
            return json.dumps({"error": "pyautogui not installed"})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def scroll(self, clicks: int = 3) -> str:
        """鼠标滚动"""
        try:
            import pyautogui
            pyautogui.scroll(clicks)
            return json.dumps({"success": True, "clicks": clicks})
        except ImportError:
            return json.dumps({"error": "pyautogui not installed"})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def get_screen_size(self) -> str:
        """获取屏幕分辨率"""
        return json.dumps({"width": self._screen_size[0], "height": self._screen_size[1]})

TOOL_DEFS = [
    {"name":"screenshot","fn":ComputerUseTool().screenshot,"desc":"截取屏幕截图","params":{},"req":[]},
    {"name":"mouse_click","fn":ComputerUseTool().mouse_click,"desc":"鼠标点击","params":{"x":{"type":"integer"},"y":{"type":"integer"},"button":{"type":"string"}},"req":["x","y"]},
    {"name":"type_text","fn":ComputerUseTool().type_text,"desc":"键盘输入","params":{"text":{"type":"string"}},"req":["text"]},
    {"name":"scroll","fn":ComputerUseTool().scroll,"desc":"鼠标滚动","params":{"clicks":{"type":"integer"}}},
    {"name":"get_screen_size","fn":ComputerUseTool().get_screen_size,"desc":"获取屏幕分辨率","params":{}},
]
