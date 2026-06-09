#!/usr/bin/env python3
"""LAAP Web Lifeform Server Launcher"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asyncio, logging
from laap.web_sdk.runtime import WebLifeformServer
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")
PORT = int(os.environ.get("LAAP_WS_PORT", "9876"))
print("=" * 56)
print("  LAAP Digital Lifeform Server")
print("=" * 56)
print(f"  WebSocket: ws://localhost:{PORT}")
print(f"  Demo:      file://{os.path.abspath('demo/index.html')}")
print("=" * 56)
server = WebLifeformServer(host="0.0.0.0", port=PORT)
asyncio.run(server.start())
