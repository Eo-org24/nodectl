from __future__ import annotations

import asyncio
import json
from importlib import import_module

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend.auth import require_admin, require_user
from backend.ledger import Ledger
from backend.routers.terminal import terminal_ws
from backend.routers.ui import home
from backend.security import SessionUser, sign_payload


def asgi_healthz(app) -> tuple[int, bytes]:
    async def _run():
        sent = False
        messages = []

        async def receive():
            nonlocal sent
            if sent:
                return {"type": "http.disconnect"}
            sent = True
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "method": "GET",
            "path": "/healthz",
            "raw_path": b"/healthz",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "root_path": "",
        }
        async with app.router.lifespan_context(app):
            await app(scope, receive, send)
        start = next(message for message in messages if message["type"] == "http.response.start")
        body = next(message for message in messages if message["type"] == "http.response.body")
        return start["status"], body["body"]

    return asyncio.run(_run())


def make_request(path: str, cookie_header: str = "") -> Request:
    headers = []
    if cookie_header:
        headers.append((b"cookie", cookie_header.encode("utf-8")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": headers,
        "query_string": b"",
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "root_path": "",
        "app": None,
    }
    return Request(scope)


class FakeWebSocket:
    def __init__(self, *, origin: str | None = None, cookie_header: str = ""):
        headers = []
        if origin is not None:
            headers.append((b"origin", origin.encode("utf-8")))
        if cookie_header:
            headers.append((b"cookie", cookie_header.encode("utf-8")))
        self.scope = {"type": "websocket", "headers": headers}
        self.headers = {key.decode("utf-8"): value.decode("utf-8") for key, value in headers}
        self.cookies = {}
        if cookie_header:
            name, value = cookie_header.split("=", 1)
            self.cookies[name] = value
        self.closed_code = None
        self.accepted = False

    async def close(self, code: int):
        self.closed_code = code

    async def accept(self):
        self.accepted = True

    async def send_text(self, _: str):
        return None

    async def receive_text(self):
        raise RuntimeError("stop")


def test_uvicorn_entrypoint_imports_and_healthz(app_settings):
    module = import_module("backend.main")
    assert module.app is not None
    status, body = asgi_healthz(module.app)
    assert status == 200
    assert json.loads(body) == {"status": "ok"}


def test_unauthenticated_http_users_cannot_access_control_functions():
    request = make_request("/api/v1/system/status")
    with pytest.raises(HTTPException) as exc:
        require_user(request)
    assert exc.value.status_code == 401


def test_non_admin_users_cannot_access_admin_functions():
    with pytest.raises(HTTPException) as exc:
        require_admin(SessionUser(username="viewer", role="viewer", csrf_token="csrf", terminal_target="factory"))
    assert exc.value.status_code == 403


def test_unauthenticated_and_wrong_origin_websockets_are_blocked(app_settings):
    websocket = FakeWebSocket(origin="http://testserver")
    asyncio.run(terminal_ws(websocket))
    assert websocket.closed_code == 4401

    session = sign_payload(
        {"sub": "admin", "role": "admin", "csrf": "csrf-token", "terminal_target": "factory"},
        app_settings.secret_key,
    )
    bad_origin_socket = FakeWebSocket(
        origin="http://evil.example",
        cookie_header=f"{app_settings.session_cookie_name}={session}",
    )
    asyncio.run(terminal_ws(bad_origin_socket))
    assert bad_origin_socket.closed_code == 4403


def test_rendered_html_and_ledger_do_not_leak_secrets(app, app_settings):
    session = sign_payload(
        {"sub": "admin", "role": "admin", "csrf": "csrf-token", "terminal_target": "factory"},
        app_settings.secret_key,
    )
    request = make_request("/", cookie_header=f"{app_settings.session_cookie_name}={session}")
    request.scope["app"] = app
    response = asyncio.run(home(request))
    html = response.body.decode("utf-8")
    assert "PRIVATE-KEY" not in html
    assert "ghp_secret" not in html

    ledger = Ledger(root=str(app_settings.ledger_root.parent), tool="nodepanel")
    ledger.write(
        actor="human:test",
        action="git.deploy",
        target="node:vm-01",
        status="ok",
        note="-----BEGIN OPENSSH PRIVATE KEY----- abcdef -----END OPENSSH PRIVATE KEY----- ghp_123456789012345678901234567890123456",
    )
    ledger_file = next(app_settings.ledger_root.glob("*.jsonl"))
    content = ledger_file.read_text(encoding="utf-8")
    assert "OPENSSH PRIVATE KEY" not in content
    assert "ghp_123456789012345678901234567890123456" not in content
