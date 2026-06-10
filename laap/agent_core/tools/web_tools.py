"""Web Tools — 搜索/抓取/网络工具"""
from __future__ import annotations
import json, urllib.request, urllib.parse, logging, re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent_core.tools.web")

def web_search(query: str, limit: int = 5) -> str:
    """搜索网络信息 (使用DuckDuckGo)"""
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "LAAP-Agent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        results = []
        if "AbstractText" in data and data["AbstractText"]:
            results.append(f"摘要: {data['AbstractText'][:500]}")
        if "RelatedTopics" in data:
            for topic in data["RelatedTopics"][:limit]:
                if "Text" in topic:
                    results.append(f"- {topic['Text'][:200]}")
        return "\n".join(results) if results else f"未找到'{query}'的相关结果"
    except Exception as e:
        return f"搜索错误: {e}"

def web_fetch(url: str) -> str:
    """获取网页内容"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LAAP-Agent/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode('utf-8', errors='replace')
        text = re.sub(r'<[^>]+>', ' ', content)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:3000]
    except Exception as e:
        return f"获取错误: {e}"

def http_get(url: str, headers: Dict = None) -> str:
    """HTTP GET请求"""
    try:
        hdrs = {"User-Agent": "LAAP-Agent/1.0", **(headers or {})}
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode('utf-8', errors='replace')
            return json.dumps({"status": resp.status, "body": body[:2000]}, ensure_ascii=False)
    except Exception as e:
        return f"HTTP错误: {e}"

def http_post(url: str, data: Dict = None, headers: Dict = None) -> str:
    """HTTP POST请求"""
    try:
        hdrs = {"User-Agent": "LAAP-Agent/1.0", "Content-Type": "application/json", **(headers or {})}
        body = json.dumps(data or {}).encode()
        req = urllib.request.Request(url, data=body, headers=hdrs, method='POST')
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode('utf-8', errors='replace')
            return json.dumps({"status": resp.status, "body": resp_body[:2000]}, ensure_ascii=False)
    except Exception as e:
        return f"HTTP错误: {e}"

TOOL_DEFS = [
    {"name":"web_search","fn":web_search,"desc":"搜索网络信息","params":{"query":{"type":"string"},"limit":{"type":"integer"}},"req":["query"]},
    {"name":"web_fetch","fn":web_fetch,"desc":"获取网页内容","params":{"url":{"type":"string"}},"req":["url"]},
    {"name":"http_get","fn":http_get,"desc":"HTTP GET请求","params":{"url":{"type":"string"},"headers":{"type":"object"}},"req":["url"]},
    {"name":"http_post","fn":http_post,"desc":"HTTP POST请求","params":{"url":{"type":"string"},"data":{"type":"object"},"headers":{"type":"object"}},"req":["url"]},
]
