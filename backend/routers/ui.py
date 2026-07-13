from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..auth import LoginPassword, LoginUsername, clear_session, configured_users, issue_session, read_session, require_csrf, require_user
from ..config import settings
from ..db import get_db
from ..ledger import read_entries


templates = Jinja2Templates(directory="templates")
router = APIRouter()


def template_context(request: Request, **extra: object) -> dict[str, object]:
    user = read_session(request)
    context = {
        "request": request,
        "session_user": user,
        "csrf_token": user.csrf_token if user else "",
    }
    context.update(extra)
    return context


def tab_context(request: Request, active_tab: str) -> dict[str, object]:
    context = template_context(request, active_tab=active_tab, read_only=True)
    user = context["session_user"]
    target_id = user.terminal_target if user else "factory"
    snapshot = request.app.state.factory_service.hypervisor_snapshot()
    context.update(
        {
            "nodes": request.app.state.factory_service.list_nodes(),
            "creds": load_repo_credentials(),
            "entries": load_ledger_entries(),
            "files": list_staging_files(),
            "vms": snapshot.vms,
            "error_msg": snapshot.error,
            "vm_ssh_user": settings.factory_user,
            "vm_ssh_key_path": settings.vm_ssh_key_path,
            "current_target_type": "host" if target_id == "factory" else "vm",
            "current_target_name": "factory" if target_id == "factory" else target_id,
        }
    )
    return context


def list_staging_files() -> list[dict[str, object]]:
    files: list[dict[str, object]] = []
    for path in sorted(settings.staging_root.rglob("*")):
        if path.is_file():
            rel_path = path.relative_to(settings.staging_root).as_posix()
            files.append({"name": rel_path, "url_name": rel_path, "size": path.stat().st_size})
    return files


def load_ledger_entries(limit: int = 100) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for ledger_file in sorted(Path(settings.ledger_root).glob("*.jsonl"), reverse=True):
        for entry in read_entries(ledger_file):
            entries.append(entry)
            if len(entries) >= limit:
                return entries
    return entries


def load_repo_credentials() -> list[dict[str, object]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT credential_id, repository_slug, environment_name, permissions, created_at, last_verified_at, status
            FROM git_credentials
            ORDER BY created_at DESC
            """
        ).fetchall()
    credentials: list[dict[str, object]] = []
    for row in rows:
        repo_slug = row["repository_slug"]
        credentials.append(
            {
                "credential_id": row["credential_id"],
                "repo_name": repo_slug,
                "node": row["environment_name"],
                "status": row["status"],
                "expires_at": row["last_verified_at"] or row["created_at"],
                "permissions": row["permissions"],
                "dest_path": f"repos/{repo_slug.split('/', 1)[-1]}",
            }
        )
    return credentials


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    if read_session(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", template_context(request))


@router.post("/login")
async def login(request: Request, response: Response, username: LoginUsername, password: LoginPassword):
    users = configured_users(settings)
    candidate = users.get(username)

    is_valid = False
    if candidate is not None:
        try:
            import pam

            pam_client = pam.pam()
            if pam_client.authenticate(username, password):
                is_valid = True
        except ImportError:
            pass

        if not is_valid and candidate.password == password:
            is_valid = True

    if not is_valid:
        return templates.TemplateResponse(
            request,
            "login.html",
            template_context(request, error="Invalid username or password."),
            status_code=401,
        )

    issue_session(response, candidate, settings)
    response.status_code = 303
    response.headers["Location"] = "/"
    return response


@router.post("/logout")
async def logout(response: Response, user=Depends(require_user), _: None = Depends(require_csrf)):
    clear_session(response, settings)
    response.status_code = 303
    response.headers["Location"] = "/login"
    return response


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = read_session(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        request,
        "index.html",
        tab_context(request, active_tab="dashboard")
        | {
            "title": settings.app_name,
            "user": user,
            "factory_host": settings.factory_host,
            "factory_port": settings.factory_port,
            "factory_user": settings.factory_user,
        },
    )


@router.get("/tab/dashboard", response_class=HTMLResponse)
async def tab_dashboard(request: Request, user=Depends(require_user)):
    return templates.TemplateResponse(request, "dashboard_tab.html", tab_context(request, active_tab="dashboard"))


@router.get("/tab/files", response_class=HTMLResponse)
async def tab_files(request: Request, user=Depends(require_user)):
    return templates.TemplateResponse(request, "files_tab.html", tab_context(request, active_tab="files"))


@router.get("/tab/repos", response_class=HTMLResponse)
async def tab_repos(request: Request, user=Depends(require_user)):
    return templates.TemplateResponse(request, "repos_tab.html", tab_context(request, active_tab="repos"))


@router.get("/tab/ledger", response_class=HTMLResponse)
async def tab_ledger(request: Request, user=Depends(require_user)):
    return templates.TemplateResponse(request, "ledger_tab.html", tab_context(request, active_tab="ledger"))


@router.get("/tab/config", response_class=HTMLResponse)
async def tab_config(request: Request, user=Depends(require_user)):
    return templates.TemplateResponse(request, "config_tab.html", tab_context(request, active_tab="config"))
