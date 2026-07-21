from __future__ import annotations

from html import escape

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..auth import require_admin, require_csrf, require_user
from ..config import settings
from ..idempotent_node_action import (
    IdempotencyConflictError, OutcomeUnknownError, run_node_action_idempotent,
)
from ..ssh_client import get_node_manifests, get_virsh_list, run_factory_script
from ..ucc_events import emit_event
from .ui import list_staging_files

IDEMPOTENCY_KEY_HEADER = "X-Idempotency-Key"


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
    nodes = await get_node_manifests()
    return templates.TemplateResponse(
        request,
        "nodes_list.html",
        {
            "request": request,
            "nodes": nodes,
            "session_user": user,
            "read_only": True,
        },
    )


@router.get("/hypervisor/vms", response_class=HTMLResponse)
async def hypervisor_vms(request: Request, user=Depends(require_user)):
    output = await get_virsh_list()
    error_msg = output if output.startswith("Error:") else None
    vms = [] if error_msg else parse_virsh_list(output)
    current_target = user.terminal_target
    return templates.TemplateResponse(
        request,
        "virsh_list.html",
        {
            "request": request,
            "vms": vms,
            "error_msg": error_msg,
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


@router.post("/nodes/{node_name}/action/{action}", response_class=HTMLResponse)
async def node_action(
    node_name: str,
    action: str,
    request: Request,
    user=Depends(require_admin),
    _: None = Depends(require_csrf),
):
    """STANDALONE-ONLY / LEGACY (UCC G1 security floor, UCC-Standards §15):
    drives allowlisted factory-side shell scripts over SSH via
    run_factory_script. Operator-only, admin+CSRF gated, diagnostic_only —
    never reachable from a future FactoryPort adapter. See
    tests/unit/test_infra_fence.py.

    An optional X-Idempotency-Key header opts into replay/conflict handling
    (M-b, D2): identical key+inputs replay the stored result instead of
    re-running the action; the same key with different inputs refuses
    (409). Omitting the header keeps today's run-every-time behavior."""
    idempotency_key = request.headers.get(IDEMPOTENCY_KEY_HEADER)
    try:
        if idempotency_key:
            from ..db import get_db
            with get_db() as conn:
                result = await run_node_action_idempotent(
                    conn, node_name=node_name, action=action,
                    idempotency_key=idempotency_key, actor_username=user.username)
        else:
            result = await run_factory_script(node_name=node_name, action=action)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=exc.problem["message"]) from exc
    except OutcomeUnknownError as exc:
        raise HTTPException(status_code=409, detail=exc.problem) from exc
    except Exception as exc:
        return render_command_result(
            request,
            command=f"{escape(action)} {escape(node_name)}",
            stdout="",
            stderr=str(exc),
            return_code=1,
        )

    if not result.get("_replayed"):
        # A replay is a cache hit, not a re-run: logging it again would
        # misrepresent history (the action did not execute a second time).
        request.app.state.ledger.write(
            actor=f"user:{user.username}",
            action=f"factory.{action}",
            target=f"node:{node_name}",
            status="ok" if result["exit_code"] == 0 else "error",
            exit=result["exit_code"],
            params={"command": result["command"]},
            note=result["stderr"] if result["exit_code"] else "",
        )
        # Dual-write (roadmap §4A "Add port + envelope stubs"): the legacy
        # ledger above stays the primary, unchanged read path; this is additive.
        emit_event(
            settings.ucc_events_root / "ucc.jsonl",
            event_type=f"node.{action}_completed" if result["exit_code"] == 0 else f"node.{action}_failed",
            subject_kind="node",
            subject_name=node_name,
            actor_username=user.username,
            payload={"action": action, "exit_code": result["exit_code"]},
        )
    return render_command_result(
        request,
        command=result["command"],
        stdout=result["stdout"],
        stderr=result["stderr"],
        return_code=result["exit_code"],
    )


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
            "request": request,
            "command": command,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": return_code,
            "retry_form": "",
        },
    )
