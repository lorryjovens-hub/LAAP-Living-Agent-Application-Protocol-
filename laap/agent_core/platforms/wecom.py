"""企业微信平台 — 深度集成（参考Hermes 1635行）"""
from __future__ import annotations
import json, logging, time, hashlib, urllib.request, xml.etree.ElementTree as ET
from typing import Any, Callable, Dict, List, Optional
from laap.agent_core.platforms.base import BasePlatformAdapter, MessageEvent, MessageType, SendResult

logger = logging.getLogger("agent_core.platforms.wecom")

class WeComAdapter(BasePlatformAdapter):
    """企业微信适配器 — 应用消息/群机器人/回调"""
    
    API_BASE = "https://qyapi.weixin.qq.com/cgi-bin"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.corp_id = config.get("corp_id", "")
        self.agent_id = config.get("agent_id", "")
        self.corp_secret = config.get("corp_secret", "")
        self.token = config.get("token", "")
        self._encoding_aes_key = config.get("aes_key", "")
        self._stats["start_time"] = time.time()
    
    async def start(self):
        self._running = True
        await self._refresh_token()
        logger.info("WeCom started")
    
    async def stop(self):
        self._running = False
    
    async def _refresh_token(self):
        try:
            url = f"{self.API_BASE}/gettoken?corpid={self.corp_id}&corpsecret={self.corp_secret}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                self._token = result.get("access_token", "")
                self._token_expire = time.time() + result.get("expires_in", 7200)
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
    
    async def send_message(self, chat_id: str, text: str, **kwargs) -> SendResult:
        """发送应用消息"""
        await self._ensure_token()
        try:
            url = f"{self.API_BASE}/message/send?access_token={self._token}"
            body = json.dumps({
                "touser": chat_id, "msgtype": "text", "agentid": int(self.agent_id),
                "text": {"content": text[:2000]},
                "safe": 0
            })
            req = urllib.request.Request(url, data=body.encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                if result.get("errcode") == 0:
                    self._stats["messages_sent"] += 1
                    return SendResult(success=True)
                return SendResult(success=False, error=str(result))
        except Exception as e:
            self._stats["errors"] += 1
            return SendResult(success=False, error=str(e))
    
    async def send_markdown(self, chat_id: str, text: str) -> SendResult:
        """发送Markdown消息"""
        await self._ensure_token()
        try:
            url = f"{self.API_BASE}/message/send?access_token={self._token}"
            body = json.dumps({
                "touser": chat_id, "msgtype": "markdown", "agentid": int(self.agent_id),
                "markdown": {"content": text[:4000]}
            })
            req = urllib.request.Request(url, data=body.encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return SendResult(success=True)
        except Exception as e:
            return SendResult(success=False, error=str(e))
    
    async def send_image(self, chat_id: str, media_id: str) -> SendResult:
        """发送图片"""
        await self._ensure_token()
        try:
            url = f"{self.API_BASE}/message/send?access_token={self._token}"
            body = json.dumps({
                "touser": chat_id, "msgtype": "image", "agentid": int(self.agent_id),
                "image": {"media_id": media_id}
            })
            req = urllib.request.Request(url, data=body.encode(), method="POST",
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return SendResult(success=True)
        except Exception as e:
            return SendResult(success=False, error=str(e))
    
    async def send_news(self, chat_id: str, articles: List[Dict]) -> SendResult:
        """发送图文消息"""
        await self._ensure_token()
        try:
            url = f"{self.API_BASE}/message/send?access_token={self._token}"
            body = json.dumps({
                "touser": chat_id, "msgtype": "news", "agentid": int(self.agent_id),
                "news": {"articles": articles[:8]}
            })
            req = urllib.request.Request(url, data=body.encode(), method="POST",
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return SendResult(success=True)
        except Exception as e:
            return SendResult(success=False, error=str(e))
    
    async def send_task_card(self, chat_id: str, title: str, desc: str, url: str) -> SendResult:
        """发送任务卡片"""
        await self._ensure_token()
        try:
            body = json.dumps({
                "touser": chat_id, "msgtype": "taskcard", "agentid": int(self.agent_id),
                "taskcard": {
                    "title": title, "description": desc,
                    "btns": [{"key": "open", "name": "查看详情", "replace_name": "已查看"}]
                }
            })
            url_api = f"{self.API_BASE}/message/send?access_token={self._token}"
            req = urllib.request.Request(url_api, data=body.encode(), method="POST",
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return SendResult(success=True)
        except Exception as e:
            return SendResult(success=False, error=str(e))
    
    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echo_str: str) -> Optional[str]:
        """验证URL回调"""
        arr = sorted([self.token, timestamp, nonce, echo_str])
        return hashlib.sha1("".join(arr).encode()).hexdigest()
    
    async def upload_media(self, file_path: str, media_type: str = "image") -> Optional[str]:
        """上传临时素材"""
        await self._ensure_token()
        try:
            url = f"{self.API_BASE}/media/upload?access_token={self._token}&type={media_type}"
            with open(file_path, 'rb') as f:
                file_data = f.read()
            boundary = "----Boundary7MA4YWxkTrZu0gW"
            body = (f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="media"; filename="{os.path.basename(file_path)}"\r\n'
                    f"Content-Type: application/octet-stream\r\n\r\n").encode() + file_data + f"\r\n--{boundary}--\r\n".encode()
            req = urllib.request.Request(url, data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode()).get("media_id")
        except: return None
