from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..auth import read_session
from ..config import settings


router = APIRouter()


@router.websocket("/api/terminal/ws")
async def terminal_ws(websocket: WebSocket):
    """STANDALONE-ONLY / LEGACY (UCC G1 security floor, UCC-Standards §15):
    this is an echo stub, not a real terminal backend, but any future real
    implementation must stay operator-only, separately audited, and never
    port-reachable or wired into automation. See tests/unit/test_infra_fence.py."""
    origin = websocket.headers.get("origin")
    if origin not in settings.allowed_origins:
        await websocket.close(code=4403)
        return
    token = websocket.cookies.get(settings.session_cookie_name)
    if not token:
        await websocket.close(code=4401)
        return
    user = read_session(websocket)
    if user is None or user.role != "admin":
        await websocket.close(code=4401)
        return
    await websocket.accept()
    await websocket.send_text(f"Connected as {user.username} to {user.terminal_target}\r\n")
    try:
        while True:
            message = await websocket.receive_text()
            payload = json.loads(message)
            if payload.get("type") == "input":
                await websocket.send_text(payload.get("data", ""))
            elif payload.get("type") == "resize":
                await websocket.send_text("")
    except WebSocketDisconnect:
        return
