from __future__ import annotations

import hashlib
import io
import tarfile
from pathlib import Path

import pytest

from backend.services.transfers import TransferError, TransferService


class FakeSFTP:
    def __init__(self, store):
        self.store = store

    def put(self, local_path, remote_path):
        self.store[remote_path] = Path(local_path).read_bytes()

    def get(self, remote_path, local_path):
        Path(local_path).write_bytes(self.store[remote_path])

    def close(self):
        return None


class FakeClient:
    def close(self):
        return None


class FakeSSHService:
    def __init__(self, settings):
        self.settings = settings
        self.store = {}
        self.last_target = None

    def vm_target(self, **kwargs):
        from backend.services.ssh import SshTarget

        return SshTarget(
            target_id=kwargs["node_id"],
            host=kwargs["host"],
            port=kwargs.get("port", 22),
            user=kwargs["user"],
            key_path=self.settings.vm_ssh_key_path,
            known_hosts_path=self.settings.ssh_known_hosts_path,
            jump_host=kwargs.get("jump_host"),
        )

    def sftp(self, target):
        self.last_target = target
        return FakeClient(), FakeSFTP(self.store)

    def run(self, target, argv, cwd=None):
        command = " ".join(argv)
        if argv[:2] == ["test", "!"] and any(path in self.store for path in self.store):
            return {"stdout": "", "stderr": "", "exit_code": 0}
        if argv[0] == "mv":
            source_prefix = argv[1].rstrip("/") + "/"
            dest_prefix = argv[2].rstrip("/") + "/"
            for key in list(self.store):
                if key.startswith(source_prefix):
                    self.store[key.replace(source_prefix, dest_prefix, 1)] = self.store.pop(key)
            return {"stdout": "", "stderr": "", "exit_code": 0}
        return {"stdout": "", "stderr": "", "exit_code": 0}

    def remote_manifest(self, target, remote_root):
        prefix = remote_root.rstrip("/") + "/"
        manifest = []
        for path, data in sorted(self.store.items()):
            if path.startswith(prefix):
                rel = path.replace(prefix, "", 1)
                manifest.append(
                    {
                        "path": rel,
                        "type": "file",
                        "size": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                    }
                )
        return manifest


def create_tarball(base_dir: Path, archive_path: Path):
    with tarfile.open(archive_path, "w") as archive:
        for path in sorted(base_dir.rglob("*")):
            if path.is_file():
                archive.add(path, arcname=path.relative_to(base_dir).as_posix())


def test_transfer_fixture_round_trips_with_identical_sha256(app_settings):
    ssh = FakeSSHService(app_settings)
    service = TransferService(ssh, app_settings)
    source = app_settings.staging_root / "fixture"
    (source / "nested").mkdir(parents=True)
    (source / "zero.txt").write_bytes(b"")
    (source / "nested" / "space name \"quoted\"\tfile.txt").write_text("payload", encoding="utf-8")
    manifest = service.build_local_manifest(source)

    target = ssh.vm_target(node_id="vm-01", host="10.0.0.10", user="ubuntu")
    service.stage_to_vm(target=target, source_path="fixture", destination_path="release")
    result = service.collect_outbox(target=target, remote_root="/home/ubuntu/payload/release")

    final_dir = Path(result["path"])
    for entry in manifest:
        data = (final_dir / entry["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]


def test_verify_archive_rejects_unmanifested_files(app_settings):
    ssh = FakeSSHService(app_settings)
    service = TransferService(ssh, app_settings)
    source = app_settings.staging_root / "archive-fixture"
    source.mkdir()
    (source / "ok.txt").write_text("ok", encoding="utf-8")
    manifest = service.build_local_manifest(source)
    archive_path = app_settings.data_root / "fixture.tar"
    with tarfile.open(archive_path, "w") as archive:
        archive.add(source / "ok.txt", arcname="ok.txt")
        extra = tarfile.TarInfo("extra.txt")
        payload = b"extra"
        extra.size = len(payload)
        archive.addfile(extra, io.BytesIO(payload))

    with pytest.raises(TransferError, match="manifest"):
        service.verify_archive(archive_path, manifest, app_settings.inbox_root / "verified")


def test_verify_archive_rejects_traversal_members(app_settings):
    ssh = FakeSSHService(app_settings)
    service = TransferService(ssh, app_settings)
    manifest = [{"path": "ok.txt", "type": "file", "size": 2, "sha256": hashlib.sha256(b"ok").hexdigest()}]
    archive_path = app_settings.data_root / "traversal.tar"
    with tarfile.open(archive_path, "w") as archive:
        evil = tarfile.TarInfo("../evil.txt")
        payload = b"ok"
        evil.size = len(payload)
        archive.addfile(evil, io.BytesIO(payload))

    with pytest.raises((TransferError, ValueError)):
        service.verify_archive(archive_path, manifest, app_settings.inbox_root / "verified")
