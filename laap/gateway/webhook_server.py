"""LAAP — Webhook HTTP Server
Receives incoming webhook POSTs, authenticates via Bearer token,
and triggers LAAP agent processing.
"""
from __future__ import annotations
import json, logging, os, sys, asyncio, hashlib, hmac
from pathlib import Path
from typing import Optional

logger = logging.getLogger("laap.gateway.webhook_server")

try:
    from fastapi import FastAPI, Request, HTTPException
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from laap.gateway.webhooks import WebhookManager, WebhookNotFoundError

webhook_app = None
_manager = WebhookManager()

def _launch_agent(name: str, payload: dict):
    import subprocess
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "laap", "run", f"--webhook={name}"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, close_fds=True)
        logger.debug("Spawned LAAP agent (PID %s) for webhook '%s'", proc.pid, name)
    except Exception as exc:
        logger.error("Failed to spawn LAAP agent: %s", exc)

if HAS_FASTAPI:
    webhook_app = FastAPI(title="LAAP Webhook Server", version="1.0.0")

    @webhook_app.get("/health")
    async def health():
        return {"status": "ok", "service": "laap-webhooks"}

    @webhook_app.post("/webhooks/{name}")
    async def receive_webhook(name: str, request: Request):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Bearer token")
        token = auth[7:]
        subs = _manager._subs()
        sub = subs.get(name)
        if sub is None:
            raise HTTPException(status_code=404, detail="Webhook not found")
        if not hmac.compare_digest(token, sub["secret"]):
            raise HTTPException(status_code=401, detail="Invalid token")
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")
        logger.info("Webhook '%s' received", name)
        _launch_agent(name, body)
        return {"status": "accepted", "webhook": name}

async def run_simple_server(host: str = "0.0.0.0", port: int = 8081):
    """Fallback asyncio HTTP server when FastAPI not available."""
    class SimpleHTTP(asyncio.Protocol):
        def __init__(self, mgr):
            self.mgr = mgr; self.buffer = b""; self.transport = None
        def connection_made(self, transport):
            self.transport = transport
        def data_received(self, data: bytes):
            self.buffer += data
            if b"\r\n\r\n" not in self.buffer:
                return
            self._handle()
        def _handle(self):
            try:
                head, _, body = self.buffer.partition(b"\r\n\r\n")
                lines = head.decode("utf-8", errors="replace").split("\r\n")
                if not lines:
                    return self._respond(400, b"Bad Request")
                method, path, _ = lines[0].split(" ", 2)
                headers = {}
                for line in lines[1:]:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        headers[k.strip().lower()] = v.strip()
                if path == "/health":
                    return self._respond(200, json.dumps({"status": "ok"}).encode())
                if method == "POST" and path.startswith("/webhooks/"):
                    name = path.split("/")[2]
                    subs = self.mgr._subs()
                    if name not in subs:
                        return self._respond(404, json.dumps({"error": "Not found"}).encode())
                    auth = headers.get("authorization", "")
                    if not auth.startswith("Bearer "):
                        return self._respond(401, json.dumps({"error": "Unauthorized"}).encode())
                    token = auth[7:]
                    if not hmac.compare_digest(token, subs[name]["secret"]):
                        return self._respond(401, json.dumps({"error": "Invalid token"}).encode())
                    payload = json.loads(body.decode("utf-8"))
                    logger.info("Simple server: webhook '%s' received", name)
                    _launch_agent(name, payload)
                    return self._respond(200, json.dumps({"status": "accepted"}).encode())
                self._respond(404, b"Not Found")
            except Exception as exc:
                logger.exception("Request error")
                self._respond(500, json.dumps({"error": str(exc)}).encode())
        def _respond(self, status: int, body: bytes, ct: str = "application/json"):
            status_map = {200: b"200 OK", 400: b"400 Bad Request", 401: b"401 Unauthorized",
                          404: b"404 Not Found", 500: b"500 Internal Server Error"}
            resp = (b"HTTP/1.1 " + status_map.get(status, b"500 Internal Server Error") + b"\r\n"
                    b"Content-Type: " + ct.encode() + b"\r\n"
                    b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                    b"Connection: close\r\n\r\n" + body)
            if self.transport:
                self.transport.write(resp)
                self.transport.close()
    loop = asyncio.get_event_loop()
    factory = lambda: SimpleHTTP(_manager)
    server = await loop.create_server(factory, host, port)
    logger.info("Simple webhook server on %s:%s", host, port)
    async with server:
        await server.serve_forever()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="LAAP Webhook Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument("--simple", action="store_true", help="Use asyncio server (no FastAPI)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    if args.simple or not HAS_FASTAPI:
        logger.info("Starting simple webhook server...")
        asyncio.run(run_simple_server(args.host, args.port))
    else:
        logger.info("Starting FastAPI webhook server on %s:%s", args.host, args.port)
        import uvicorn
        uvicorn.run("laap.gateway.webhook_server:webhook_app", host=args.host, port=args.port, reload=False)

if __name__ == "__main__":
    main()
