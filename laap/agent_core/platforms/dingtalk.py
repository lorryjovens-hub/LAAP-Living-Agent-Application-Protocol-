"""钉钉平台 — 深度集成（参考Hermes 1503行）"""
from __future__ import annotations
import json, logging, time, hashlib, base64, hmac, urllib.request
from typing import Any, Callable, Dict, List, Optional
from laap.agent_core.platforms.base import BasePlatformAdapter, MessageEvent, MessageType, SendResult

logger = logging.getLogger("agent_core.platforms.dingtalk")

class DingTalkAdapter(BasePlatformAdapter):
    """钉钉适配器 — 机器人消息/Webhook/Stream模式"""
    
    API_BASE = "https://oapi.dingtalk.com"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.app_key = config.get("app_key", "") or config.get("app_id", "")
        self.app_secret = config.get("app_secret", "")
        self._webhook_url = config.get("webhook", "")
        self._webhook_secret = config.get("webhook_secret", "")
        self._stats["start_time"] = time.time()
    
    async def start(self):
        self._running = True
        await self._refresh_token()
        logger.info("DingTalk started")
    
    async def stop(self):
        self._running = False
    
    async def _refresh_token(self):
        try:
            url = f"{self.API_BASE}/gettoken?appkey={self.app_key}&appsecret={self.app_secret}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                self._token = result.get("access_token", "")
                self._token_expire = time.time() + result.get("expires_in", 7200)
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
    
    async def send_message(self, chat_id: str, text: str, **kwargs) -> SendResult:
        """发送消息"""
        if self._webhook_url:
            return await self._send_webhook(text)
        return await self._send_api(chat_id, text)
    
    async def _send_webhook(self, text: str) -> SendResult:
        """通过Webhook发送"""
        try:
            url = self._webhook_url
            if self._webhook_secret:
                timestamp = str(int(time.time() * 1000))
                sign = base64.b64encode(
                    hmac.new(self._webhook_secret.encode(),
                            f"{timestamp}\n{self._webhook_secret}".encode(),
                            hashlib.sha256).digest()
                ).decode()
                url += f"&timestamp={timestamp}&sign={sign}"
            body = json.dumps({"msgtype": "text", "text": {"content": text[:2000]}})
            req = urllib.request.Request(url, data=body.encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                self._stats["messages_sent"] += 1
                return SendResult(success=True)
        except Exception as e:
            self._stats["errors"] += 1
            return SendResult(success=False, error=str(e))
    
    async def _send_api(self, chat_id: str, text: str) -> SendResult:
        """通过API发送"""
        await self._ensure_token()
        try:
            url = f"{self.API_BASE}/topapi/message/corpconversation/asyncsend_v2?access_token={self._token}"
            body = json.dumps({
                "agent_id": self.config.get("agent_id", ""),
                "userid_list": chat_id,
                "msg": {"msgtype": "text", "text": {"content": text[:2000]}}
            })
            req = urllib.request.Request(url, data=body.encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return SendResult(success=True)
        except Exception as e:
            return SendResult(success=False, error=str(e))
    
    async def send_markdown(self, chat_id: str, title: str, text: str) -> SendResult:
        """发送Markdown消息"""
        if self._webhook_url:
            url = self._webhook_url
            if self._webhook_secret:
                timestamp = str(int(time.time() * 1000))
                sign = base64.b64encode(
                    hmac.new(self._webhook_secret.encode(),
                            f"{timestamp}\n{self._webhook_secret}".encode(),
                            hashlib.sha256).digest()
                ).decode()
                url += f"&timestamp={timestamp}&sign={sign}"
            body = json.dumps({"msgtype": "markdown", "markdown": {"title": title, "text": text[:5000]}})
            req = urllib.request.Request(url, data=body.encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return SendResult(success=True)
        return SendResult(success=False, error="webhook required for markdown")
    
    async def send_action_card(self, chat_id: str, title: str, text: str,
                                 btn_orientation: str = "1", btns: List[Dict] = None) -> SendResult:
        """发送行动卡片"""
        if not self._webhook_url: return SendResult(success=False, error="webhook required")
        url = self._webhook_url
        if self._webhook_secret:
            timestamp = str(int(time.time() * 1000))
            sign = base64.b64encode(
                hmac.new(self._webhook_secret.encode(),
                        f"{timestamp}\n{self._webhook_secret}".encode(),
                        hashlib.sha256).digest()
            ).decode()
            url += f"&timestamp={timestamp}&sign={sign}"
        card = {
            "title": title, "text": text, "btnOrientation": btn_orientation,
            "btns": btns or [{"title": "确定", "actionURL": ""}]
        }
        body = json.dumps({"msgtype": "actionCard", "actionCard": card})
        req = urllib.request.Request(url, data=body.encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return SendResult(success=True)
    
    async def get_user_info(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        await self._ensure_token()
        try:
            url = f"{self.API_BASE}/topapi/v2/user/get?access_token={self._token}"
            body = json.dumps({"userid": user_id}).encode()
            req = urllib.request.Request(url, data=body, method="POST",
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode()).get("result")
        except: return None
