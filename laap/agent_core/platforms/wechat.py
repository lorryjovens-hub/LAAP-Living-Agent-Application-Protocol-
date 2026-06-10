"""微信公众平台 — 深度集成（参考Hermes 2358行）"""
from __future__ import annotations
import json, logging, time, hashlib, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from typing import Any, Callable, Dict, List, Optional
from laap.agent_core.platforms.base import BasePlatformAdapter, MessageEvent, MessageType, SendResult

logger = logging.getLogger("agent_core.platforms.wechat")

class WeChatAdapter(BasePlatformAdapter):
    """微信公众号/小程序适配器 — 完整消息处理"""
    
    API_BASE = "https://api.weixin.qq.com/cgi-bin"
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.app_id = config.get("app_id", "")
        self.app_secret = config.get("app_secret", "")
        self.token = config.get("token", "")
        self._aes_key = config.get("aes_key", "")
        self._stats["start_time"] = time.time()
    
    def verify_signature(self, signature: str, timestamp: str, nonce: str) -> bool:
        """验证微信服务器签名"""
        arr = sorted([self.token, timestamp, nonce])
        return hashlib.sha1("".join(arr).encode()).hexdigest() == signature
    
    async def start(self):
        self._running = True
        await self._refresh_token()
        logger.info("WeChat started")
    
    async def stop(self):
        self._running = False
    
    async def _refresh_token(self):
        """获取access_token"""
        try:
            url = f"{self.API_BASE}/token?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                self._token = result.get("access_token", "")
                self._token_expire = time.time() + result.get("expires_in", 7200)
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
    
    async def send_message(self, chat_id: str, text: str, **kwargs) -> SendResult:
        """发送客服消息"""
        await self._ensure_token()
        try:
            url = f"{self.API_BASE}/message/custom/send?access_token={self._token}"
            body = json.dumps({
                "touser": chat_id, "msgtype": "text",
                "text": {"content": text[:2000]}
            })
            req = urllib.request.Request(url, data=body.encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                if result.get("errcode") == 0:
                    self._stats["messages_sent"] += 1
                    return SendResult(success=True)
                return SendResult(success=False, error=result.get("errmsg", ""))
        except Exception as e:
            self._stats["errors"] += 1
            return SendResult(success=False, error=str(e))
    
    async def send_image(self, chat_id: str, media_id: str) -> SendResult:
        """发送图片消息"""
        await self._ensure_token()
        try:
            url = f"{self.API_BASE}/message/custom/send?access_token={self._token}"
            body = json.dumps({
                "touser": chat_id, "msgtype": "image",
                "image": {"media_id": media_id}
            })
            req = urllib.request.Request(url, data=body.encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return SendResult(success=True)
        except Exception as e:
            return SendResult(success=False, error=str(e))
    
    async def send_news(self, chat_id: str, articles: List[Dict]) -> SendResult:
        """发送图文消息"""
        await self._ensure_token()
        try:
            url = f"{self.API_BASE}/message/custom/send?access_token={self._token}"
            body = json.dumps({
                "touser": chat_id, "msgtype": "news",
                "news": {"articles": articles[:8]}
            })
            req = urllib.request.Request(url, data=body.encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return SendResult(success=True)
        except Exception as e:
            return SendResult(success=False, error=str(e))
    
    def parse_xml_message(self, xml_data: str) -> Dict:
        """解析微信XML消息"""
        root = ET.fromstring(xml_data)
        msg = {}
        for child in root:
            msg[child.tag] = child.text
        return msg
    
    def build_text_reply(self, to_user: str, from_user: str, content: str) -> str:
        """构建文本回复XML"""
        import time
        return f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""
    
    def build_news_reply(self, to_user: str, from_user: str, articles: List[Dict]) -> str:
        """构建图文回复XML"""
        items = ""
        for a in articles[:10]:
            items += f"""<item>
<Title><![CDATA[{a.get('title','')}]]></Title>
<Description><![CDATA[{a.get('description','')}]]></Description>
<PicUrl><![CDATA[{a.get('picurl','')}]]></PicUrl>
<Url><![CDATA[{a.get('url','')}]]></Url>
</item>"""
        return f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[news]]></MsgType>
<ArticleCount>{len(articles)}</ArticleCount>
<Articles>{items}</Articles>
</xml>"""
    
    async def upload_media(self, file_path: str, media_type: str = "image") -> Optional[str]:
        """上传素材"""
        await self._ensure_token()
        try:
            url = f"{self.API_BASE}/media/upload?access_token={self._token}&type={media_type}"
            with open(file_path, 'rb') as f:
                file_data = f.read()
            import io, cgi
            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="media"; filename="{os.path.basename(file_path)}"\r\n'
                f"Content-Type: application/octet-stream\r\n\r\n"
            ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()
            req = urllib.request.Request(url, data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode()).get("media_id")
        except: return None
    
    async def create_menu(self, menu_data: Dict) -> bool:
        """创建自定义菜单"""
        await self._ensure_token()
        try:
            url = f"{self.API_BASE}/menu/create?access_token={self._token}"
            req = urllib.request.Request(url, data=json.dumps(menu_data).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return True
        except: return False
