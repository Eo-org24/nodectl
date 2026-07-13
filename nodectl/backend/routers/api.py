from __future__ import annotations

from html import escape

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..auth import require_admin, require_csrf, require_user
from ..services.git_credentials import GitCredentialError
from ..services.ssh import SshTarget
from ..services.transfers import TransferError
from .ui import list_staging_files


router = APIRouter(prefix="/api")
templates = Jinja2Templates(directory="templates")


@router.get("/v1/system/status")
async def system_status(request: Request, user=Depends(require_user)):
    ssh_service = request.app.state.ssh_service
    target = ssh_service.factory_target()
    snapshot = request.app.state.factory_service.hypervisor_snapshot()
    nodes = request.app.state.factory_service.list_nodes()
    return {
        "user": user.username,
        "factory": {
            "host": target.host,
            "port": target.port,
            "user": target.user,
        },
        "stats": {
            "manifests": len(nodes),
            "vms": len(snapshot.vms),
            "running": sum(1 for vm in snapshot.vms if vm["state"] == "running"),
        },
    }


@router.get("/nodes", response_class=HTMLResponse)
async def list_nodes(request: Request, user=Depends(require_user)):
    nodes = request.app.state.factory_service.list_nodes()
    return templates.TemplateResponse(request, "nodes_list.html", {"request": request, "nodes": nodes, "read_only": True})


@router.get("/hypervisor/vms", response_class=HTMLResponse)
async def hypervisor_vms(request: Request, user=Depends(require_user)):
    snapshot = request.app.state.factory_service.hypervisor_snapshot()
    current_target = user.terminal_target
    return templates.TemplateResponse(
        request,
        "virsh_list.html",
        {
            "request": request,
            "vms": snapshot.vms,
            "error_msg": snapshot.error,
            "current_target_type": "host" if current_target == "factory" else "vm",
            "current_target_name": "factory" if current_target == "factory" else current_target,
            "read_only": True,
        },
    )


@router.get("/files/list", response_class=HTMLResponse)
async def files_list(request: Request, user=Depends(require_user)):
    files = list_staging_files()
    return templates.TemplateResponse(
        request,
        "components/files_list.html",
        {"request": request, "files": files, "read_only": True},
    )


@router.post("/terminal/target")
async def set_terminal_target(
    request: Request,
    payload: dict,
    user=Depends(require_admin),
    _: None = Depends(require_csrf),
):
    target_id = payload.get("target_id")
    if not isinstance(target_id, str) or not target_id:
        raise HTTPException(status_code=400, detail="target_id is required.")
    response = request.app.state.session_response_factory(request, user, target_id)
    return response


@router.post("/host-keys/probe")
async def probe_host_key(request: Request, payload: dict, user=Depends(require_admin), _: None = Depends(require_csrf)):
    host = payload.get("host")
    port = int(payload.get("port", 22))
    return request.app.state.host_key_service.probe(host, port)


@router.post("/host-keys/approve")
async def approve_host_key(request: Request, payload: dict, user=Depends(require_admin), _: None = Depends(require_csrf)):
    return request.app.state.host_key_service.approve(
        target_id=str(payload["target_id"]),
        host=str(payload["host"]),
        port=int(payload.get("port", 22)),
        approved_by=user.username,
    )


@router.post("/transfers/collect")
async def collect_outbox(request: Request, payload: dict, user=Depends(require_admin), _: None = Depends(require_csrf)):
    ssh_service = request.app.state.ssh_service
    transfer_service = request.app.state.transfer_service
    target = ssh_service.vm_target(
        node_id=str(payload["node_id"]),
        host=str(payload["host"]),
        user=str(payload["user"]),
        port=int(payload.get("port", 22)),
        key_identifier=str(payload.get("key_identifier", "vm")),
        jump_host=payload.get("jump_host"),
    )
    try:
        return transfer_service.collect_outbox(target=target, remote_root=str(payload["remote_root"]))
    except TransferError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message}) from exc


@router.post("/transfers/stage")
async def stage_to_vm(request: Request, payload: dict, user=Depends(require_admin), _: None = Depends(require_csrf)):
    ssh_service = request.app.state.ssh_service
    transfer_service = request.app.state.transfer_service
    target = ssh_service.vm_target(
        node_id=str(payload["node_id"]),
        host=str(payload["host"]),
        user=str(payload["user"]),
        port=int(payload.get("port", 22)),
        key_identifier=str(payload.get("key_identifier", "vm")),
        jump_host=payload.get("jump_host"),
    )
    try:
        return transfer_service.stage_to_vm(
            target=target,
            source_path=str(payload["source_path"]),
            destination_path=str(payload["destination_path"]),
        )
    except TransferError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message}) from exc


@router.post("/git/deploy-keys")
async def create_deploy_key(request: Request, payload: dict, user=Depends(require_admin), _: None = Depends(require_csrf)):
    ssh_service = request.app.state.ssh_service
    service = request.app.state.git_credential_service
    target = ssh_service.vm_target(
        node_id=str(payload["node_id"]),
        host=str(payload["host"]),
        user=str(payload["user"]),
        port=int(payload.get("port", 22)),
        key_identifier="vm",
        jump_host=payload.get("jump_host"),
    )
    try:
        return service.provision_deploy_key(
            target=target,
            repository_slug=str(payload["repository_slug"]),
            environment_name=str(payload.get("environment_name", "default")),
            credential_id=str(payload.get("credential_id") or uuid4_hex()),
            private_key=str(payload["private_key"]),
            public_key=str(payload["public_key"]),
            permissions=str(payload.get("permissions", "read-only")),
        )
    except GitCredentialError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message}) from exc


@router.post("/git/deploy-keys/scrub")
async def scrub_deploy_key(request: Request, payload: dict, user=Depends(require_admin), _: None = Depends(require_csrf)):
    ssh_service = request.app.state.ssh_service
    service = request.app.state.git_credential_service
    target = ssh_service.vm_target(
        node_id=str(payload["node_id"]),
        host=str(payload["host"]),
        user=str(payload["user"]),
        port=int(payload.get("port", 22)),
        key_identifier="vm",
        jump_host=payload.get("jump_host"),
    )
    try:
        return service.scrub(
            target=target,
            credential_id=str(payload["credential_id"]),
            repository_slug=str(payload["repository_slug"]),
        )
    except GitCredentialError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message}) from exc


def uuid4_hex() -> str:
    import uuid

    return uuid.uuid4().hex[:12]


def parse_virsh_list(output: str) -> list[dict[str, str]]:
    vms: list[dict[str, str]] = []
    lines = output.splitlines()
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and all(char in "- " for char in stripped):
            start_idx = i + 1
            break
    else:
        start_idx = min(2, len(lines))

    for raw_line in lines[start_idx:]:
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=2)
        if len(parts) < 2:
            continue
        vm_id = parts[0]
        name = parts[1]
        state = parts[2] if len(parts) > 2 else "unknown"
        vms.append({"id": vm_id, "name": name, "state": state})
    return vms


def render_command_result(request: Request, *, command: str, stdout: str, stderr: str, return_code: int) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "components/command_result.html",
        {
            "command": command,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": return_code,
            "retry_form": "",
        },
    )
