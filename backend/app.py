from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from .auth import issue_session
from .config import settings
from .db import init_db
from .ledger import Ledger
from .routers import api, health, terminal, ui
from .services.factory import FactoryService
from .services.git_credentials import GitCredentialService
from .services.host_keys import HostKeyService
from .services.ssh import SSHService
from .services.transfers import TransferService


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.health_ready = False
    app.state.health_error = ""
    try:
        settings.ensure_directories()
        settings.validate_runtime()
        init_db()
        app.state.health_ready = True
        yield
    except Exception as exc:
        app.state.health_error = str(exc)
        raise
    finally:
        app.state.health_ready = False


def create_app() -> FastAPI:
    settings.ensure_directories()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.state.health_ready = False
    app.state.ssh_service = SSHService(settings)
    app.state.factory_service = FactoryService(app.state.ssh_service, settings)
    app.state.host_key_service = HostKeyService(app.state.ssh_service)
    app.state.transfer_service = TransferService(app.state.ssh_service, settings)
    app.state.git_credential_service = GitCredentialService(app.state.ssh_service, settings)
    app.state.ledger = Ledger(root=str(settings.ledger_root.parent), tool="nodepanel")

    def session_response_factory(request: Request, user, target_id: str) -> Response:
        response = JSONResponse({"status": "ok", "target_id": target_id})
        issue_session(response, user, settings, terminal_target=target_id)
        return response

    app.state.session_response_factory = session_response_factory

    app.include_router(health.router)
    app.include_router(ui.router)
    app.include_router(api.router)
    app.include_router(terminal.router)

    app.mount("/static", StaticFiles(directory="static"), name="static")
    if Path("frontend/dist/assets").exists():
        app.mount("/app/assets", StaticFiles(directory="frontend/dist/assets"), name="vue_assets")

    @app.get("/app")
    @app.get("/app/")
    @app.get("/app/{full_path:path}")
    async def serve_vue(full_path: str = ""):
        dist_index = Path("frontend/dist/index.html")
        if not dist_index.exists():
            return JSONResponse({"detail": "Vue frontend build not found."}, status_code=404)
        return FileResponse(dist_index)

    return app
