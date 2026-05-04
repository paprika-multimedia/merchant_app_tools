import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from config import WS_AUTH_TIMEOUT_SECONDS, WS_HEARTBEAT_SECONDS
from websocket.events import ping_event

logger = logging.getLogger(__name__)

# Registry of all authenticated WebSocket connections.
# Maps websocket → True (set semantics, WebSocket is not hashable in all versions
# so we use a list and a lock).
_connections: list[WebSocket] = []
_lock = asyncio.Lock()


async def register(ws: WebSocket) -> None:
    async with _lock:
        _connections.append(ws)


async def unregister(ws: WebSocket) -> None:
    async with _lock:
        try:
            _connections.remove(ws)
        except ValueError:
            pass


async def broadcast(event: dict[str, Any]) -> None:
    """Send an event to every authenticated client. Failed sends are silently dropped."""
    payload = json.dumps(event)
    async with _lock:
        recipients = list(_connections)
    for ws in recipients:
        try:
            await ws.send_text(payload)
        except Exception:
            pass


async def ws_endpoint(websocket: WebSocket) -> None:
    """Handle a WebSocket connection at /v1/stream.

    Auth-frame protocol (Spec §5.1):
    1. Client must send { "type": "auth", "token": "<session_token>" } within WS_AUTH_TIMEOUT_SECONDS.
    2. Server replies { "type": "auth.ok" }.
    3. Any non-auth frame before auth.ok → close with 4400.
    4. Invalid/missing token → close with 4401.
    5. After auth: server sends heartbeat pings every WS_HEARTBEAT_SECONDS seconds.
    """
    await websocket.accept()

    # --- Auth handshake ---
    try:
        raw = await asyncio.wait_for(
            websocket.receive_text(),
            timeout=float(WS_AUTH_TIMEOUT_SECONDS),
        )
    except asyncio.TimeoutError:
        await websocket.close(code=4401)
        return
    except WebSocketDisconnect:
        return

    try:
        frame = json.loads(raw)
    except json.JSONDecodeError:
        await websocket.close(code=4400)
        return

    if frame.get("type") != "auth":
        # Non-auth frame received before auth.ok — close 4400.
        await websocket.close(code=4400)
        return

    token = frame.get("token", "")
    if not token or not isinstance(token, str):
        await websocket.close(code=4401)
        return

    # Simulator accepts any non-empty token as valid.
    await websocket.send_text(json.dumps({"type": "auth.ok"}))
    await register(websocket)

    # --- Main loop: heartbeat + receive client frames ---
    try:
        while True:
            try:
                raw_msg = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=float(WS_HEARTBEAT_SECONDS),
                )
                # The simulator doesn't process client frames after auth.
                # Just discard them gracefully.
                logger.debug("WS received (ignored): %s", raw_msg)
            except asyncio.TimeoutError:
                # Heartbeat interval elapsed — send ping.
                try:
                    await websocket.send_text(json.dumps(ping_event()))
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await unregister(websocket)
