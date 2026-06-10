"""Email Platform — IMAP/SMTP邮件"""
from __future__ import annotations
import json, logging, smtplib, imaplib, email
from email.mime.text import MIMEText
from typing import Any, Callable, Dict, List, Optional
from laap.agent_core.platforms.base import BasePlatformAdapter, MessageEvent, SendResult

logger = logging.getLogger("agent_core.platforms.email")

class EmailAdapter(BasePlatformAdapter):
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.smtp_server = config.get("smtp_server", "smtp.gmail.com")
        self.smtp_port = config.get("smtp_port", 587)
        self.imap_server = config.get("imap_server", "imap.gmail.com")
        self.email_addr = config.get("email", "")
        self.password = config.get("password", "")
    
    async def start(self):
        self._running = True
        logger.info(f"Email started: {self.email_addr}")
    
    async def stop(self):
        self._running = False
    
    async def send_message(self, to_addr: str, text: str, **kwargs) -> SendResult:
        try:
            msg = MIMEText(text[:50000], "plain", "utf-8")
            msg["Subject"] = kwargs.get("subject", "LAAP Message")
            msg["From"] = self.email_addr
            msg["To"] = to_addr
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_addr, self.password)
                server.send_message(msg)
            return SendResult(success=True)
        except Exception as e:
            return SendResult(success=False, error=str(e))
