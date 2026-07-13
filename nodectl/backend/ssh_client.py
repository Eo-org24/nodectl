from __future__ import annotations

import asyncio
import shlex
from pathlib import PurePosixPath
from typing import Any

import yaml
from fabric import Connection

from .config import settings


ACTION_LABELS = {
    "assign": "assign",
    "snapshot": "snapshot",
    "destroy": "destroy",
}


def _connect() -> Connection:
    return Connection(
        host=settings.factory_host,
        user=settings.factory_user,
        port=settings.factory_port,
        connect_kwargs={
            "key_filename": str(settings.factory_ssh_key_path),
            "look_for_keys": False,
            "allow_agent": False,
        },
    )


def _normalize_manifest_value(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def normalize_manifest_record(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    manifest_path = PurePosixPath(path)
    spec = payload.get("spec") if isinstance(payload.get("spec"), dict) else {}
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}

    name = (
        _normalize_manifest_value(payload, "name", "node_name", "hostname")
        or _normalize_manifest_value(metadata, "name")
        or manifest_path.parent.name
        or manifest_path.stem
    )
    node_type = (
        _normalize_manifest_value(payload, "type", "kind", "role", "template")
        or _normalize_manifest_value(spec, "type", "role", "template")
        or "worker"
    )
    state = (
        _normalize_manifest_value(payload, "state", "status", "lifecycle")
        or _normalize_manifest_value(spec, "state", "status")
        or "unknown"
    )

    return {
        "name": name,
        "type": node_type,
        "state": state,
        "path": path,
        "manifest": payload,
    }


def _read_factory_manifests_sync() -> list[dict[str, Any]]:
    if settings.mock_ssh:
        return []

    connection = _connect()
    manifests: list[dict[str, Any]] = []
    try:
        listing = connection.run(
            f"cd {settings.factory_dir} && "
            "find nodes -type f \\( -name 'node.yaml' -o -name '*.yaml' \\) | sort",
            hide=True,
            warn=True,
        )
        if listing.exited != 0:
            return []

        for rel_path in [line.strip() for line in listing.stdout.splitlines() if line.strip()]:
            result = connection.run(
                f"cd {settings.factory_dir} && cat {shlex.quote(rel_path)}",
                hide=True,
                warn=True,
            )
            if result.exited != 0:
                continue
            payload = yaml.safe_load(result.stdout) or {}
            if isinstance(payload, dict):
                manifests.append(normalize_manifest_record(rel_path, payload))
    finally:
        connection.close()
    return manifests


async def get_node_manifests() -> list[dict[str, Any]]:
    manifests = await asyncio.to_thread(_read_factory_manifests_sync)
    return sorted(manifests, key=lambda item: item["name"])


def _build_factory_action_command(node_name: str, action: str) -> str:
    label = ACTION_LABELS[action]
    safe_name = shlex.quote(node_name)
    safe_action = shlex.quote(label)
    return (
        f"cd {settings.factory_dir} && "
        f"action={safe_action} node_name={safe_name} bash -lc '"
        "script=\"\"; "
        "for candidate in "
        "\"./${action}.sh\" "
        "\"./scripts/${action}.sh\" "
        "\"./bin/${action}.sh\" "
        "\"./scripts/factory/${action}.sh\"; do "
        "  if [ -x \"$candidate\" ]; then script=\"$candidate\"; break; fi; "
        "done; "
        "if [ -z \"$script\" ]; then "
        "  echo \"No executable found for action ${action} in $PWD\" >&2; "
        "  exit 127; "
        "fi; "
        "\"$script\" \"$node_name\"'"
    )


def _run_factory_action_sync(node_name: str, action: str) -> dict[str, Any]:
    if action not in ACTION_LABELS:
        raise ValueError(f"Unsupported action: {action}")
    if settings.mock_ssh:
        command = _build_factory_action_command(node_name, action)
        return {
            "command": command,
            "stdout": f"[mock] {action} {node_name}",
            "stderr": "",
            "exit_code": 0,
        }

    connection = _connect()
    command = _build_factory_action_command(node_name, action)
    try:
        result = connection.run(command, hide=True, warn=True)
        return {
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exited,
        }
    finally:
        connection.close()


async def run_factory_script(node_name: str, action: str) -> dict[str, Any]:
    return await asyncio.to_thread(_run_factory_action_sync, node_name, action)


def _get_virsh_list_sync() -> str:
    if settings.mock_ssh:
        return " Id   Name   State\n----------------------\n -    watcher  shut off\n"

    connection = _connect()
    try:
        result = connection.run("virsh list --all", hide=True, warn=True)
        if result.exited != 0:
            stderr = result.stderr.strip() or "virsh list failed"
            return f"Error: {stderr}"
        return result.stdout
    finally:
        connection.close()


async def get_virsh_list() -> str:
    return await asyncio.to_thread(_get_virsh_list_sync)
