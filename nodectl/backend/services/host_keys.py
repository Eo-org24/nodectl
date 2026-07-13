from __future__ import annotations

from datetime import datetime, timezone

from ..db import get_db
from .ssh import SSHService


class HostKeyService:
    def __init__(self, ssh_service: SSHService):
        self.ssh_service = ssh_service

    def probe(self, host: str, port: int) -> dict[str, str]:
        return self.ssh_service.discover_host_key(host, port)

    def approve(self, *, target_id: str, host: str, port: int, approved_by: str) -> dict[str, str]:
        discovered = self.probe(host, port)
        known_hosts_line = f"[{host}]:{port} {discovered['key']}\n"
        with self.ssh_service.settings.ssh_known_hosts_path.open("a", encoding="utf-8") as handle:
            handle.write(known_hosts_line)
        timestamp = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO host_keys(target_id, hostname, port, algorithm, fingerprint, approved_at, approved_by, changed_at, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, '')
                ON CONFLICT(target_id) DO UPDATE SET
                    hostname = excluded.hostname,
                    port = excluded.port,
                    algorithm = excluded.algorithm,
                    fingerprint = excluded.fingerprint,
                    approved_at = excluded.approved_at,
                    approved_by = excluded.approved_by,
                    changed_at = excluded.approved_at
                """,
                (
                    target_id,
                    host,
                    port,
                    discovered["algorithm"],
                    discovered["fingerprint"],
                    timestamp,
                    approved_by,
                ),
            )
        return discovered
