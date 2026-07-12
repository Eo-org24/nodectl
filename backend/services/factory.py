from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import yaml

from ..config import Settings, settings
from .ssh import SSHService


@dataclass(frozen=True)
class HypervisorSnapshot:
    vms: list[dict[str, str]]
    error: str | None = None


class FactoryService:
    def __init__(self, ssh_service: SSHService, app_settings: Settings = settings):
        self.ssh_service = ssh_service
        self.settings = app_settings

    def list_nodes(self) -> list[dict[str, Any]]:
        if self.settings.mock_ssh:
            return [
                {"name": "w-cliplib-01", "type": "ai-worker", "state": "assigned"},
                {"name": "w-cliplib-02", "type": "ai-worker", "state": "idle"},
                {"name": "w-webserver-01", "type": "web-server", "state": "active"},
            ]

        script = (
            "import json, pathlib\n"
            "files = []\n"
            "for path in sorted(pathlib.Path('nodes').glob('*/node.yaml')):\n"
            "    files.append(path.read_text(encoding='utf-8'))\n"
            "print(json.dumps(files))\n"
        )
        result = self.ssh_service.run(
            self.ssh_service.factory_target(),
            ["python3", "-c", script],
            cwd=self.settings.factory_dir,
        )
        if result["exit_code"] != 0:
            return []
        manifests = json.loads(result["stdout"] or "[]")
        nodes: list[dict[str, Any]] = []
        for manifest in manifests:
            parsed = yaml.safe_load(manifest)
            if isinstance(parsed, dict):
                nodes.append(parsed)
        return nodes

    def hypervisor_snapshot(self) -> HypervisorSnapshot:
        if self.settings.mock_ssh:
            return HypervisorSnapshot(
                vms=[
                    {"id": "1", "name": "w-cliplib-01", "state": "running"},
                    {"id": "2", "name": "w-webserver-01", "state": "running"},
                    {"id": "-", "name": "w-cliplib-02", "state": "shut off"},
                ]
            )

        result = self.ssh_service.run(
            self.ssh_service.factory_target(),
            ["virsh", "-c", "qemu:///system", "list", "--all"],
        )
        if result["exit_code"] != 0:
            message = result["stderr"].strip() or "Unable to query hypervisor state."
            return HypervisorSnapshot(vms=[], error=message)
        return HypervisorSnapshot(vms=self._parse_virsh_list(result["stdout"]))

    @staticmethod
    def _parse_virsh_list(output: str) -> list[dict[str, str]]:
        vms: list[dict[str, str]] = []
        for raw_line in output.splitlines():
            line = raw_line.rstrip()
            if not line or line.lstrip().startswith("Id") or set(line.strip()) == {"-"}:
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            vm_id = parts[0]
            name = parts[1]
            state = " ".join(parts[2:])
            vms.append({"id": vm_id, "name": name, "state": state})
        return vms
