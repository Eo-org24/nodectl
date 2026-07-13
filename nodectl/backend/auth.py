from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Annotated

from fastapi import Depends, Form, HTTPException, Request, Response, status

from .config import Settings, settings
from .security import SessionUser, new_csrf_token, sign_payload, unsign_payload


@dataclass(frozen=True)
class AuthRecord:
    username: str
    password: str
    role: str


def session_cookie_payload(user: AuthRecord, csrf_token: str, terminal_target: str = "factory") -> dict:
    return {
        "sub": user.username,
        "role": user.role,
        "csrf": csrf_token,
        "terminal_target": terminal_target,
    }


def configured_users(app_settings: Settings) -> dict[str, AuthRecord]:
    return {
        app_settings.admin_username: AuthRecord(
            username=app_settings.admin_username,
            password=app_settings.admin_password,
            role="admin",
        ),
        app_settings.viewer_username: AuthRecord(
            username=app_settings.viewer_username,
            password=app_settings.viewer_password,
            role="viewer",
        ),
    }


def issue_session(response: Response, user: Any, app_settings: Settings, terminal_target: str = "factory") -> str:
    csrf_token = new_csrf_token()
    token = sign_payload(session_cookie_payload(user, csrf_token, terminal_target), app_settings.secret_key)
    response.set_cookie(
        app_settings.session_cookie_name,
        token,
        httponly=True,
        secure=app_settings.secure_cookies,
        samesite="lax",
        max_age=app_settings.session_max_age_seconds,
        path="/",
    )
    return csrf_token


def clear_session(response: Response, app_settings: Settings) -> None:
    response.delete_cookie(app_settings.session_cookie_name, path="/")


def read_session(request_like: Any, app_settings: Settings = settings) -> SessionUser | None:
    token = request_like.cookies.get(app_settings.session_cookie_name)
    if not token:
        return None
    payload = unsign_payload(token, app_settings.secret_key)
    if not payload:
        return None
    username = payload.get("sub")
    role = payload.get("role")
    csrf = payload.get("csrf")
    terminal_target = payload.get("terminal_target", "factory")
    if not all(isinstance(item, str) and item for item in (username, role, csrf, terminal_target)):
        return None
    return SessionUser(username=username, role=role, csrf_token=csrf, terminal_target=terminal_target)


def require_user(request: Request) -> SessionUser:
    user = read_session(request)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


def require_admin(user: Annotated[SessionUser, Depends(require_user)]) -> SessionUser:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required.")
    return user


async def require_csrf(
    request: Request,
    user: Annotated[SessionUser, Depends(require_user)],
) -> None:
    token = request.headers.get(settings.csrf_header_name)
    if token is None:
        form = await request.form()
        token = form.get("csrf_token")
    if token != user.csrf_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token.")


LoginUsername = Annotated[str, Form(...)]
LoginPassword = Annotated[str, Form(...)]
