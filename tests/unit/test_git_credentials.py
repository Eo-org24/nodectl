from __future__ import annotations

import pytest

from backend.db import get_db
from backend.services.git_credentials import GitCredentialError, GitCredentialService
from backend.services.ssh import SshTarget


class FakeSFTP:
    def __init__(self):
        self.uploads = {}

    def put(self, local_path, remote_path):
        self.uploads[remote_path] = remote_path

    def close(self):
        return None


class FakeClient:
    def close(self):
        return None


class FakeSSHService:
    def __init__(self, settings):
        self.settings = settings
        self.sftp_client = FakeSFTP()
        self.commands = []
        self.fail_verify = False
        self.scrubbed = False

    def sftp(self, target):
        return FakeClient(), self.sftp_client

    def run(self, target, argv, cwd=None):
        self.commands.append((tuple(argv), cwd))
        if argv[:3] == ["git", "ls-remote", "origin"]:
            if self.scrubbed or self.fail_verify:
                return {"stdout": "", "stderr": "permission denied", "exit_code": 1}
            return {"stdout": "deadbeef\tHEAD\n", "stderr": "", "exit_code": 0}
        if argv[:2] == ["rm", "-f"]:
            self.scrubbed = True
        return {"stdout": "", "stderr": "", "exit_code": 0}


@pytest.fixture()
def target(app_settings):
    return SshTarget(
        target_id="vm-01",
        host="10.0.0.10",
        port=22,
        user="ubuntu",
        key_path=app_settings.vm_ssh_key_path,
        known_hosts_path=app_settings.ssh_known_hosts_path,
    )


def test_git_deploy_key_marks_live_only_after_ls_remote(app_settings, target):
    fake_ssh = FakeSSHService(app_settings)
    service = GitCredentialService(fake_ssh, app_settings)

    result = service.provision_deploy_key(
        target=target,
        repository_slug="owner/repo",
        environment_name="prod",
        credential_id="cred-001",
        private_key="PRIVATE-KEY",
        public_key="PUBLIC-KEY",
    )

    assert result["status"] == "live"
    with get_db() as conn:
        row = conn.execute("SELECT * FROM git_credentials WHERE credential_id = 'cred-001'").fetchone()
    assert row["status"] == "live"
    assert "PRIVATE-KEY" not in "".join(str(value) for value in row)


def test_invalid_git_key_never_creates_live_record(app_settings, target):
    fake_ssh = FakeSSHService(app_settings)
    fake_ssh.fail_verify = True
    service = GitCredentialService(fake_ssh, app_settings)

    with pytest.raises(GitCredentialError):
        service.provision_deploy_key(
            target=target,
            repository_slug="owner/repo",
            environment_name="prod",
            credential_id="cred-002",
            private_key="PRIVATE-KEY",
            public_key="PUBLIC-KEY",
        )

    with get_db() as conn:
        row = conn.execute("SELECT * FROM git_credentials WHERE credential_id = 'cred-002'").fetchone()
    assert row is None


def test_scrub_removes_remote_key_and_verifies_failure(app_settings, target):
    fake_ssh = FakeSSHService(app_settings)
    service = GitCredentialService(fake_ssh, app_settings)
    service.provision_deploy_key(
        target=target,
        repository_slug="owner/repo",
        environment_name="prod",
        credential_id="cred-003",
        private_key="PRIVATE-KEY",
        public_key="PUBLIC-KEY",
    )

    result = service.scrub(target=target, credential_id="cred-003", repository_slug="owner/repo")

    assert result["status"] == "scrubbed"
    with get_db() as conn:
        row = conn.execute("SELECT status FROM git_credentials WHERE credential_id = 'cred-003'").fetchone()
    assert row["status"] == "scrubbed"


def test_git_credentials_schema_does_not_persist_remote_key_paths(app_settings):
    with get_db() as conn:
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(git_credentials)")
        }
    assert "remote_path" not in columns
