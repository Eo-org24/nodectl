from __future__ import annotations

import hashlib
import json
import shlex
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import paramiko

from ..config import Settings, settings


@dataclass(frozen=True)
class SshTarget:
    target_id: str
    host: str
    port: int
    user: str
    key_path: Path
    known_hosts_path: Path
    jump_host: str | None = None


class SSHService:
    def __init__(self, app_settings: Settings = settings):
        self.settings = app_settings

    def factory_target(self) -> SshTarget:
        return SshTarget(
            target_id="factory",
            host=self.settings.factory_host,
            port=self.settings.factory_port,
            user=self.settings.factory_user,
            key_path=self.settings.factory_ssh_key_path,
            known_hosts_path=self.settings.ssh_known_hosts_path,
        )

    def vm_target(
        self,
        *,
        node_id: str,
        host: str,
        user: str,
        port: int = 22,
        key_identifier: str = "vm",
        jump_host: str | None = None,
    ) -> SshTarget:
        if key_identifier != "vm":
            raise ValueError("Unsupported VM SSH key identifier.")
        return SshTarget(
            target_id=node_id,
            host=host,
            port=port,
            user=user,
            key_path=self.settings.vm_ssh_key_path,
            known_hosts_path=self.settings.ssh_known_hosts_path,
            jump_host=jump_host,
        )

    def _build_client(self, target: SshTarget) -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        client.load_host_keys(str(target.known_hosts_path))
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        client.connect(
            hostname=target.host,
            port=target.port,
            username=target.user,
            key_filename=str(target.key_path),
            look_for_keys=False,
            allow_agent=self.settings.ssh_use_agent,
            timeout=self.settings.ssh_connect_timeout_seconds,
        )
        return client

    def run(self, target: SshTarget, argv: list[str], *, cwd: str | None = None) -> dict[str, Any]:
        command = shlex.join(argv)
        if cwd:
            command = f"cd {shlex.quote(cwd)} && {command}"
        client = self._build_client(target)
        try:
            stdin, stdout, stderr = client.exec_command(command, timeout=self.settings.ssh_connect_timeout_seconds)
            exit_code = stdout.channel.recv_exit_status()
            return {
                "stdout": stdout.read().decode("utf-8", errors="replace"),
                "stderr": stderr.read().decode("utf-8", errors="replace"),
                "exit_code": exit_code,
            }
        finally:
            client.close()

    def sftp(self, target: SshTarget):
        client = self._build_client(target)
        try:
            sftp = client.open_sftp()
        except Exception:
            client.close()
            raise
        return client, sftp

    def discover_host_key(self, host: str, port: int) -> dict[str, str]:
        sock = socket.create_connection((host, port), timeout=self.settings.ssh_connect_timeout_seconds)
        transport = paramiko.Transport(sock)
        try:
            transport.start_client(timeout=self.settings.ssh_connect_timeout_seconds)
            remote_key = transport.get_remote_server_key()
            return {
                "algorithm": remote_key.get_name(),
                "fingerprint": hashlib.sha256(remote_key.asbytes()).hexdigest(),
                "key": f"{remote_key.get_name()} {remote_key.get_base64()}",
            }
        finally:
            transport.close()
            sock.close()

    def remote_manifest(self, target: SshTarget, remote_root: str) -> list[dict[str, Any]]:
        script = (
            "import hashlib, json, pathlib, sys\n"
            "root = pathlib.Path(sys.argv[1]).expanduser().resolve()\n"
            "files = []\n"
            "for path in sorted(root.rglob('*')):\n"
            "    if path.is_symlink():\n"
            "        raise SystemExit('symlink-not-allowed')\n"
            "    if path.is_file():\n"
            "        rel = path.relative_to(root).as_posix()\n"
            "        digest = hashlib.sha256(path.read_bytes()).hexdigest()\n"
            "        files.append({'path': rel, 'type': 'file', 'size': path.stat().st_size, 'sha256': digest})\n"
            "print(json.dumps(files, ensure_ascii=False))\n"
        )
        result = self.run(target, ["python3", "-c", script, remote_root])
        if result["exit_code"] != 0:
            raise RuntimeError("Unable to generate remote manifest.")
        return json.loads(result["stdout"])

    def diagnose(self, target: SshTarget) -> dict[str, Any]:
        try:
            self.run(target, ["true"])
        except paramiko.BadHostKeyException:
            return {"target": target.target_id, "status": "failed", "code": "bad_host_key"}
        except paramiko.SSHException:
            return {"target": target.target_id, "status": "failed", "code": "ssh_error"}
        except OSError:
            return {"target": target.target_id, "status": "failed", "code": "network_error"}
        return {"target": target.target_id, "status": "ok", "code": "authenticated"}
