"""LAAP MCP — OAuth Support

OAuth 2.0 flow for MCP servers that require authentication.
Supports authorization code flow with local redirect server.
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode, urlparse, parse_qs

logger = logging.getLogger("laap.mcp.oauth")

TOKEN_DIR = Path.home() / ".laap" / "mcp" / "tokens"


def _ensure_token_dir():
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)


def _token_path(server_name: str) -> Path:
    safe = server_name.replace("/", "_").replace(" ", "_")
    return TOKEN_DIR / f"{safe}_oauth.json"


def _find_free_port() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handles the OAuth callback with the authorization code."""
    server_instance: "LocalOAuthServer | None" = None

    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        code = qs.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        if code:
            msg = "<h1>\U00002705 Authorization successful!</h1><p>You can close this window.</p>"
            if self.server_instance:
                self.server_instance.auth_code = code
        else:
            msg = "<h1>\U0000274C Authorization failed!</h1>"
        self.wfile.write(msg.encode("utf-8"))

    def log_message(self, fmt, *args):
        pass  # Suppress HTTP log


class LocalOAuthServer:
    """Temporary local HTTP server for OAuth callback."""

    def __init__(self):
        self.auth_code: Optional[str] = None
        self.server: Optional[HTTPServer] = None

    def start(self, port: int):
        OAuthCallbackHandler.server_instance = self
        self.server = HTTPServer(("127.0.0.1", port), OAuthCallbackHandler)

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server = None


async def oauth_flow(server_name: str, auth_url: str,
                     token_url: str, client_id: str,
                     client_secret: str = "",
                     scopes: Optional[list] = None) -> bool:
    """Complete OAuth 2.0 authorization code flow.

    Returns True if tokens were obtained and saved.
    """
    port = _find_free_port()
    redirect_uri = f"http://127.0.0.1:{port}"

    # Build authorization URL
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes or ["openid", "profile"]),
    }
    full_auth_url = f"{auth_url}?{urlencode(params)}"

    # Start local server
    server = LocalOAuthServer()
    server.start(port)

    # Open browser
    logger.info(f"Opening browser for OAuth: {server_name}")
    webbrowser.open(full_auth_url)

    # Wait for callback (non-blocking)
    import threading
    thread = threading.Thread(target=server.server.serve_forever, daemon=True)
    thread.start()

    # Poll for auth code
    timeout = 120
    for _ in range(timeout * 10):
        await asyncio.sleep(0.1)
        if server.auth_code:
            break

    server.stop()

    if not server.auth_code:
        logger.error("OAuth: timeout waiting for authorization")
        return False

    # Exchange code for tokens
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(token_url, data={
                "grant_type": "authorization_code",
                "code": server.auth_code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            })
            tokens = resp.json()
            if "access_token" in tokens:
                _ensure_token_dir()
                _token_path(server_name).write_text(
                    json.dumps(tokens, indent=2), encoding="utf-8"
                )
                logger.info(f"OAuth: tokens saved for {server_name}")
                return True
            else:
                logger.error(f"OAuth: token exchange failed: {tokens}")
                return False
    except Exception as e:
        logger.error(f"OAuth: token exchange error: {e}")
        return False


def get_token(server_name: str) -> Optional[Dict]:
    """Get saved OAuth tokens for a server."""
    path = _token_path(server_name)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


def has_token(server_name: str) -> bool:
    """Check if OAuth tokens exist for a server."""
    return _token_path(server_name).exists()


def remove_token(server_name: str) -> bool:
    """Remove OAuth tokens for a server."""
    path = _token_path(server_name)
    if path.exists():
        path.unlink()
        return True
    return False
