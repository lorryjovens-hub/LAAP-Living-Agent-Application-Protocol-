"""LAAP — Voice Interface (xiaozhi-esp32 Bridge)

Real-time voice interaction via WebSocket protocol.
"""
from __future__ import annotations
import asyncio, json, logging, time
from typing import Any, Callable, Dict, Optional, Set

logger = logging.getLogger("laap.lifeform.voice")


class XiaoZhiBridge:
    """WebSocket bridge to xiaozhi-esp32 hardware devices."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self._connections: Set[Any] = set()
        self._on_voice: Optional[Callable] = None
        self._on_text: Optional[Callable] = None
        self._running = False
        self._stats = {"messages_received": 0, "messages_sent": 0, "devices_connected": 0}

    def on_voice(self, callback: Callable):
        """Register callback for voice input."""
        self._on_voice = callback

    def on_text(self, callback: Callable):
        """Register callback for text input."""
        self._on_text = callback

    async def start(self):
        """Start WebSocket server."""
        try:
            import websockets
            self._running = True

            async def handler(websocket):
                self._connections.add(websocket)
                self._stats["devices_connected"] = len(self._connections)
                addr = websocket.remote_address
                logger.info(f"Device connected: {addr}")

                try:
                    async for raw in websocket:
                        try:
                            data = json.loads(raw)
                            self._stats["messages_received"] += 1
                            msg_type = data.get("type", "text")
                            content = data.get("content", "")

                            response = None
                            if msg_type == "voice" and self._on_voice:
                                response = await self._on_voice(content, data)
                            elif msg_type == "text" and self._on_text:
                                response = await self._on_text(content, data)
                            else:
                                # Echo back for testing
                                response = {"type": "echo", "content": content}

                            if response:
                                await websocket.send(json.dumps(response))
                                self._stats["messages_sent"] += 1

                        except json.JSONDecodeError:
                            await websocket.send(json.dumps({
                                "type": "error", "content": "Invalid JSON"
                            }))
                except Exception as e:
                    logger.debug(f"Device disconnected: {e}")
                finally:
                    self._connections.discard(websocket)
                    self._stats["devices_connected"] = len(self._connections)

            self._server = await websockets.serve(handler, self.host, self.port)
            logger.info(f"Voice server: ws://{self.host}:{self.port}")
            await self._server.wait_closed()

        except ImportError:
            logger.error("pip install websockets")
        except Exception as e:
            logger.error(f"Voice server error: {e}")

    async def broadcast(self, message: dict):
        """Send to all connected devices."""
        if not self._connections:
            return
        msg = json.dumps(message)
        disconnected = set()
        for conn in self._connections:
            try:
                await conn.send(msg)
                self._stats["messages_sent"] += 1
            except Exception:
                disconnected.add(conn)
        self._connections -= disconnected

    async def send_to(self, device_id: str, message: dict):
        """Send to specific device."""
        # Implementation depends on device identification
        pass

    async def stop(self):
        self._running = False
        if hasattr(self, '_server') and self._server:
            self._server.close()

    @property
    def stats(self) -> dict:
        return dict(self._stats)

    @property
    def device_count(self) -> int:
        return len(self._connections)
