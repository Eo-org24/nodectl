from __future__ import annotations

import hashlib
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..config import Settings, settings
from ..db import get_db
from .ssh import SSHService, SshTarget


REPO_SLUG_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
CREDENTIAL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,31}$")


class GitCredentialError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class GitCredentialService:
    def __init__(self, ssh_service: SSHService, app_settings: Settings = settings):
        self.ssh_service = ssh_service
        self.settings = app_settings

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def validate_repo_slug(self, slug: str) -> str:
        if not REPO_SLUG_RE.fullmatch(slug):
            raise GitCredentialError("invalid_slug", "Repository slug must match owner/repository.")
        return slug

    def validate_credential_id(self, credential_id: str) -> str:
        if not CREDENTIAL_ID_RE.fullmatch(credential_id):
            raise GitCredentialError("invalid_credential_id", "Credential ID contains unsupported characters.")
        return credential_id

    def _remote_key_path(self, credential_id: str) -> str:
        return f"~/.ssh/nodepanel/{credential_id}"

    def _remote_home(self, target: SshTarget) -> str:
        return f"/home/{target.user}"

    def _fingerprint(self, public_key: str) -> str:
        return hashlib.sha256(public_key.encode("utf-8")).hexdigest()

    def provision_deploy_key(
        self,
        *,
        target: SshTarget,
        repository_slug: str,
        environment_name: str,
        credential_id: str,
        private_key: str,
        public_key: str,
        permissions: str = "read-only",
    ) -> dict[str, str]:
        slug = self.validate_repo_slug(repository_slug)
        cred_id = self.validate_credential_id(credential_id)
        remote_home = self._remote_home(target)
        remote_key_path = f"{remote_home}/.ssh/nodepanel/{cred_id}"
        if not self.settings.github_known_hosts_entry:
            raise GitCredentialError("missing_github_host_key", "GitHub known_hosts entry is not configured.")
        temp_key = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8")
        temp_known_hosts = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8")
        try:
            temp_key.write(private_key)
            temp_key.flush()
            temp_known_hosts.write(self.settings.github_known_hosts_entry + "\n")
            temp_known_hosts.flush()
            client, sftp = self.ssh_service.sftp(target)
            try:
                self.ssh_service.run(target, ["mkdir", "-p", f"{remote_home}/.ssh/nodepanel"])
                remote_tmp = f"{remote_key_path}.tmp"
                sftp.put(temp_key.name, remote_tmp)
                self.ssh_service.run(target, ["chmod", "0600", remote_tmp])
                self.ssh_service.run(target, ["mv", remote_tmp, remote_key_path])
                self.ssh_service.run(target, ["mkdir", "-p", f"{remote_home}/.ssh"])
                github_known_hosts = f"{remote_home}/.ssh/nodepanel_github_known_hosts"
                sftp.put(temp_known_hosts.name, github_known_hosts)
                repo_name = slug.split("/", 1)[1]
                remote_url = f"git@github.com:{slug}.git"
                ssh_command = f"ssh -i {remote_key_path} -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile={github_known_hosts}"
                repo_path = f"{remote_home}/repos/{repo_name}"
                self.ssh_service.run(target, ["mkdir", "-p", repo_path])
                self.ssh_service.run(target, ["git", "init", repo_path])
                self.ssh_service.run(target, ["git", "remote", "remove", "origin"], cwd=repo_path)
                self.ssh_service.run(target, ["git", "remote", "add", "origin", remote_url], cwd=repo_path)
                self.ssh_service.run(target, ["git", "config", "core.sshCommand", ssh_command], cwd=repo_path)
                verification = self.ssh_service.run(target, ["git", "ls-remote", "origin", "HEAD"], cwd=repo_path)
                if verification["exit_code"] != 0 or "HEAD" not in verification["stdout"]:
                    raise GitCredentialError("verification_failed", "git ls-remote origin HEAD failed.")
            finally:
                sftp.close()
                client.close()
        finally:
            Path(temp_key.name).unlink(missing_ok=True)
            Path(temp_known_hosts.name).unlink(missing_ok=True)
        now = self._timestamp()
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO git_credentials(
                    credential_id, repository_slug, environment_name, public_key_fingerprint,
                    permissions, created_at, last_verified_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'live')
                """,
                (
                    cred_id,
                    slug,
                    environment_name,
                    self._fingerprint(public_key),
                    permissions,
                    now,
                    now,
                ),
            )
        return {"credential_id": cred_id, "status": "live"}

    def scrub(self, *, target: SshTarget, credential_id: str, repository_slug: str) -> dict[str, str]:
        cred_id = self.validate_credential_id(credential_id)
        remote_home = self._remote_home(target)
        remote_key_path = f"{remote_home}/.ssh/nodepanel/{cred_id}"
        repo_name = self.validate_repo_slug(repository_slug).split("/", 1)[1]
        repo_path = f"{remote_home}/repos/{repo_name}"
        self.ssh_service.run(target, ["rm", "-f", remote_key_path])
        self.ssh_service.run(target, ["git", "config", "--unset-all", "core.sshCommand"], cwd=repo_path)
        verification = self.ssh_service.run(target, ["git", "ls-remote", "origin", "HEAD"], cwd=repo_path)
        if verification["exit_code"] == 0:
            raise GitCredentialError("scrub_incomplete", "Credential still authenticates after scrub.")
        with get_db() as conn:
            conn.execute(
                "UPDATE git_credentials SET status = 'scrubbed', last_verified_at = ? WHERE credential_id = ?",
                (self._timestamp(), cred_id),
            )
        return {"credential_id": cred_id, "status": "scrubbed"}
