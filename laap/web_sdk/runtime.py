"""LAAP Web Runtime — 数字生命体 WebSocket 运行时"""
from __future__ import annotations
import asyncio, json, logging, time
from typing import Any, Dict, Optional, Set

from laap.protocol.laap_id import create_identity
from laap.protocol.laap_com import get_bus, MessageIntent, Message
from laap.protocol.laap_life import LifecycleStateMachine, LifeEvent, LifeEventType, LifeStage
from laap.protocol.laap_mem import MemoryStore, MemoryRecord, MemoryLevel

logger = logging.getLogger("laap.web.runtime")


class WebLifeform:
    def __init__(self, name: str = "Web-Spirit", site_url: str = ""):
        self.identity = create_identity(name=name)
        self.site_url = site_url
        self.lifecycle = LifecycleStateMachine(LifeStage.BORN)
        self.lifecycle.trigger(LifeEvent(LifeEventType.INIT_COMPLETE))
        self.memory = MemoryStore()
        self.bus = get_bus()
        self._connections: Set[Any] = set()
        self.stats = {"messages": 0, "started_at": time.time()}

    @property
    def uptime_hours(self) -> float:
        return (time.time() - self.stats["started_at"]) / 3600

    def record_interaction(self, data: Dict):
        self.lifecycle.trigger(LifeEvent(LifeEventType.INTERACTION))
        self.memory.store(MemoryRecord(
            level=MemoryLevel.EPISODIC, type="event",
            content=json.dumps(data, ensure_ascii=False)[:500], importance=0.5))
        self.stats["messages"] += 1

    def to_dict(self) -> dict:
        return {
            "identity": self.identity.to_dict(),
            "lifecycle": self.lifecycle.to_dict(),
            "memory": self.memory.get_stats(),
            "uptime_hours": round(self.uptime_hours, 2),
        }


class WebLifeformServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 9876):
        self.host = host
        self.port = port
        self._lifeforms: Dict[str, WebLifeform] = {}

    async def start(self):
        import websockets
        logger.info(f"LAAP Server starting on ws://{self.host}:{self.port}")
        async def handler(websocket):
            lf = WebLifeform(name="Web-Spirit")
            self._lifeforms[lf.identity.id] = lf
            await websocket.send(json.dumps({
                "type": "laap_identity", "data": lf.identity.to_dict(),
            }))
            logger.info(f"Lifeform: {lf.identity.short_id()}")
            try:
                async for raw in websocket:
                    data = json.loads(raw)
                    t = data.get("type", "")
                    if t == "interaction":
                        lf.record_interaction(data.get("data", {}))
                        await websocket.send(json.dumps({
                            "type": "ack", "message_id": data.get("message_id", ""),
                        }))
                    elif t == "get_status":
                        await websocket.send(json.dumps({"type": "status", "data": lf.to_dict()}))
            except: pass
            finally: self._lifeforms.pop(lf.identity.id, None)
        async with websockets.serve(handler, self.host, self.port):
            await asyncio.Future()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    srv = WebLifeformServer()
    asyncio.run(srv.start())
