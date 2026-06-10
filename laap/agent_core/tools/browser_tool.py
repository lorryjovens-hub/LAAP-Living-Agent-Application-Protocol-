"""Browser Tool — 浏览器自动化(导航/点击/输入/截图)"""
from __future__ import annotations
import time, json, logging, urllib.request, urllib.parse, re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent_core.tools.browser")

class BrowserTool:
    def __init__(self):
        self._pages: Dict[str, str] = {}
    
    def navigate(self, url: str) -> str:
        """导航到URL并获取内容"""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LAAP-Agent/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode('utf-8', errors='replace')
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text).strip()
            title = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
            self._pages[url] = text
            return json.dumps({"url": url, "title": title.group(1) if title else url,
                              "content_length": len(text), "content": text[:2000]}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def extract_links(self, url: str) -> str:
        """提取页面所有链接"""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LAAP-Agent/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode('utf-8', errors='replace')
            links = re.findall(r'href=["\'](https?://[^"\']+)["\']', html)
            return json.dumps({"url": url, "links": links[:50], "total": len(links)}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def get_page(self, url: str) -> str:
        """获取已缓存的页面内容"""
        content = self._pages.get(url, "")
        if content:
            return content[:3000]
        return self.navigate(url)

TOOL_DEFS = [
    {"name":"browser_navigate","fn":BrowserTool().navigate,"desc":"导航到网页","params":{"url":{"type":"string"}},"req":["url"]},
    {"name":"browser_links","fn":BrowserTool().extract_links,"desc":"提取页面链接","params":{"url":{"type":"string"}},"req":["url"]},
]
