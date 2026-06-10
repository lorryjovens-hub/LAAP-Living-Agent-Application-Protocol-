"""Android SDK Stub"""
from __future__ import annotations
import logging
logger = logging.getLogger("sdk.mobile.android")

class AndroidSDK:
    def __init__(self, app_id: str = ""):
        self.app_id = app_id
    def initialize(self, context: dict = None) -> bool:
        logger.info(f"Android SDK initialized: {self.app_id}")
        return True
    def get_device_info(self) -> dict:
        return {"platform": "android", "sdk_version": "1.0"}
    def show_notification(self, title: str, body: str):
        logger.info(f"Notification: {title} - {body}")
