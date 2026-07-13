from __future__ import annotations

import hashlib
import json
import os
import posixpath
import shutil
import tarfile
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..config import Settings, settings
from ..db import get_db
from ..paths import safe_join
from .ssh import SSHService, SshTarget


TRANSFER_ACTIVE = {"queued", "preparing", "transferring", "verifying", "committed"}
TRANSFER_TERMINAL = {"completed", "failed", "cancelled"}


@dataclass(frozen=True)
class TransferLimits:
    max_bytes: int
    max_files: int
    max_file_bytes: int


class TransferError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class TransferService:
    def __init__(self, ssh_service: SSHService, app_settings: Settings = settings):
        self.ssh_service = ssh_service
        self.settings = app_settings
        self.limits = TransferLimits(
            max_bytes=app_settings.max_transfer_bytes,
            max_files=app_settings.max_transfer_files,
            max_file_bytes=app_settings.max_individual_file_bytes,
        )

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _remote_home(self, target: SshTarget) -> str:
        return f"/home/{target.user}"

    def create_record(self, *, direction: str, node_id: str, source: str, destination: str) -> str:
        transfer_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO transfer_records(
                    transfer_id, direction, node_id, source, destination, status, created_at
                ) VALUES (?, ?, ?, ?, ?, 'queued', ?)
                """,
                (transfer_id, direction, node_id, source, destination, self._timestamp()),
            )
        return transfer_id

    def update_record(self, transfer_id: str, **updates: object) -> None:
        columns = ", ".join(f"{key} = ?" for key in updates)
        values = list(updates.values()) + [transfer_id]
        with get_db() as conn:
            conn.execute(f"UPDATE transfer_records SET {columns} WHERE transfer_id = ?", values)

    def _manifest_digest(self, manifest: list[dict[str, object]]) -> str:
        payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _resolve_manifest_relative_path(self, root: Path, relative_path: str) -> Path:
        if not relative_path or "\x00" in relative_path:
            raise TransferError("invalid_path", "Manifest contains an invalid path.")
        if relative_path.startswith("/"):
            raise TransferError("absolute_path", "Manifest paths must be relative.")
        parts = relative_path.split("/")
        if any(part in ("", ".", "..") for part in parts):
            raise TransferError("invalid_path", "Manifest path traversal is not allowed.")
        normalized = posixpath.normpath(relative_path)
        if normalized.startswith("../") or normalized == "..":
            raise TransferError("invalid_path", "Manifest path traversal is not allowed.")
        resolved_root = root.resolve()
        candidate = (resolved_root / Path(*parts)).resolve()
        if not candidate.is_relative_to(resolved_root):
            raise TransferError("invalid_path", "Manifest path escapes the managed root.")
        return candidate

    def _validate_manifest(self, manifest: list[dict[str, object]]) -> tuple[int, int]:
        if len(manifest) > self.limits.max_files:
            raise TransferError("too_many_files", "File-count limit exceeded.")
        total_bytes = 0
        seen_paths: set[str] = set()
        for entry in manifest:
            rel_path = str(entry["path"])
            if rel_path in seen_paths:
                raise TransferError("duplicate_path", "Manifest contains duplicate paths.")
            seen_paths.add(rel_path)
            self._resolve_manifest_relative_path(Path("/managed-root"), rel_path)
            if entry.get("type") != "file":
                raise TransferError("unsupported_type", "Only regular files are supported.")
            size = int(entry["size"])
            if size > self.limits.max_file_bytes:
                raise TransferError("file_too_large", "Individual file-size limit exceeded.")
            total_bytes += size
        if total_bytes > self.limits.max_bytes:
            raise TransferError("bytes_limit", "Transfer byte limit exceeded.")
        return len(manifest), total_bytes

    def verify_archive(self, archive_path: Path, manifest: list[dict[str, object]], destination_root: Path) -> Path:
        file_count, total_bytes = self._validate_manifest(manifest)
        manifest_map = {str(item["path"]): item for item in manifest}
        extraction_root = Path(tempfile.mkdtemp(prefix="extract-", dir=destination_root.parent))
        seen_paths: set[str] = set()
        try:
            with tarfile.open(archive_path, "r:*") as archive:
                for member in archive.getmembers():
                    member_path = member.name
                    self._resolve_manifest_relative_path(extraction_root, member_path)
                    if member.islnk() or member.issym() or member.isdev() or member.isfifo():
                        raise TransferError("unsupported_member", "Archive contains unsupported link or device members.")
                    if member.isdir():
                        continue
                    if not member.isfile():
                        raise TransferError("unsupported_member", "Archive contains unsupported members.")
                    if member_path not in manifest_map:
                        raise TransferError("unmanifested_file", "Archive contains a file missing from the manifest.")
                    target = self._resolve_manifest_relative_path(extraction_root, member_path)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        raise TransferError("missing_member", "Archive member could not be read.")
                    digest = hashlib.sha256()
                    written = 0
                    with target.open("wb") as handle:
                        while chunk := extracted.read(65536):
                            written += len(chunk)
                            if written > self.limits.max_file_bytes:
                                raise TransferError("file_too_large", "Extracted file exceeded the size limit.")
                            digest.update(chunk)
                            handle.write(chunk)
                        handle.flush()
                        os.fsync(handle.fileno())
                    expected = manifest_map[member_path]
                    if written != int(expected["size"]):
                        raise TransferError("size_mismatch", "Extracted file size mismatch.")
                    if digest.hexdigest() != expected["sha256"]:
                        raise TransferError("sha256_mismatch", "Extracted file digest mismatch.")
                    seen_paths.add(member_path)
            if seen_paths != set(manifest_map):
                raise TransferError("missing_manifest_entry", "Archive is missing files declared in the manifest.")
            self._fsync_tree(extraction_root)
            final_root = destination_root
            extraction_root.replace(final_root)
            return final_root
        except Exception:
            shutil.rmtree(extraction_root, ignore_errors=True)
            raise

    def _fsync_tree(self, root: Path) -> None:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                with path.open("rb") as handle:
                    os.fsync(handle.fileno())

    def collect_outbox(self, *, target: SshTarget, remote_root: str) -> dict[str, object]:
        transfer_id = self.create_record(direction="download", node_id=target.target_id, source=remote_root, destination=str(self.settings.inbox_root))
        partial_dir = self.settings.inbox_root / target.target_id / f"{transfer_id}.partial"
        partial_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.update_record(transfer_id, status="preparing", started_at=self._timestamp())
            manifest = self.ssh_service.remote_manifest(target, remote_root)
            file_count, total_bytes = self._validate_manifest(manifest)
            self.update_record(
                transfer_id,
                status="transferring",
                file_count=file_count,
                total_bytes=total_bytes,
                manifest_sha256=self._manifest_digest(manifest),
            )
            client, sftp = self.ssh_service.sftp(target)
            transferred = 0
            try:
                for entry in manifest:
                    relative = str(entry["path"])
                    local_path = self._resolve_manifest_relative_path(partial_dir, relative)
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    remote_path = f"{remote_root.rstrip('/')}/{relative}"
                    sftp.get(remote_path, str(local_path))
                    transferred += local_path.stat().st_size
                    self.update_record(transfer_id, transferred_bytes=transferred)
            finally:
                sftp.close()
                client.close()
            self.update_record(transfer_id, status="verifying")
            tar_path = partial_dir / "bundle.tar"
            with tarfile.open(tar_path, "w") as archive:
                for entry in manifest:
                    archive.add(self._resolve_manifest_relative_path(partial_dir, str(entry["path"])), arcname=str(entry["path"]))
            final_dir = self.settings.inbox_root / target.target_id / transfer_id
            self.update_record(transfer_id, status="committed")
            committed_dir = self.verify_archive(tar_path, manifest, final_dir)
            shutil.rmtree(partial_dir, ignore_errors=True)
            self.update_record(transfer_id, status="completed", completed_at=self._timestamp(), destination=str(committed_dir))
            return {"transfer_id": transfer_id, "status": "completed", "path": str(committed_dir)}
        except TransferError as exc:
            self.update_record(transfer_id, status="failed", completed_at=self._timestamp(), error_code=exc.code, error_message=exc.message)
            shutil.rmtree(partial_dir, ignore_errors=True)
            raise

    def build_local_manifest(self, root: Path) -> list[dict[str, object]]:
        manifest: list[dict[str, object]] = []
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise TransferError("symlink_not_allowed", "Symlinks are not supported.")
            if path.is_file():
                rel = path.relative_to(root).as_posix()
                size = path.stat().st_size
                if size > self.limits.max_file_bytes:
                    raise TransferError("file_too_large", "Individual file-size limit exceeded.")
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                manifest.append({"path": rel, "type": "file", "size": size, "sha256": digest})
        self._validate_manifest(manifest)
        return manifest

    def stage_to_vm(self, *, target: SshTarget, source_path: str, destination_path: str) -> dict[str, object]:
        local_root = safe_join(self.settings.staging_root, source_path)
        destination_root = Path("/managed-destination")
        destination = safe_join(destination_root, destination_path).relative_to(destination_root).as_posix()
        transfer_id = self.create_record(direction="upload", node_id=target.target_id, source=str(local_root), destination=destination)
        manifest = self.build_local_manifest(local_root)
        file_count, total_bytes = self._validate_manifest(manifest)
        remote_home = self._remote_home(target)
        incoming = f"{remote_home}/payload/.incoming/{transfer_id}"
        final_dest = f"{remote_home}/payload/{destination.strip('/')}"
        try:
            self.update_record(
                transfer_id,
                status="preparing",
                started_at=self._timestamp(),
                file_count=file_count,
                total_bytes=total_bytes,
                manifest_sha256=self._manifest_digest(manifest),
            )
            client, sftp = self.ssh_service.sftp(target)
            try:
                self.ssh_service.run(target, ["mkdir", "-p", incoming])
                transferred = 0
                for entry in manifest:
                    relative = str(entry["path"])
                    local_path = self._resolve_manifest_relative_path(local_root, relative)
                    remote_path = f"{incoming}/{relative}"
                    parent = remote_path.rsplit("/", 1)[0]
                    self.ssh_service.run(target, ["mkdir", "-p", parent])
                    sftp.put(str(local_path), remote_path)
                    transferred += local_path.stat().st_size
                    self.update_record(transfer_id, status="transferring", transferred_bytes=transferred)
            finally:
                sftp.close()
                client.close()
            remote_manifest = self.ssh_service.remote_manifest(target, incoming)
            if remote_manifest != manifest:
                raise TransferError("remote_mismatch", "Remote manifest verification failed.")
            conflict = self.ssh_service.run(target, ["test", "!", "-e", final_dest])
            if conflict["exit_code"] != 0:
                raise TransferError("destination_conflict", "Destination already exists.")
            self.update_record(transfer_id, status="verifying")
            self.ssh_service.run(target, ["mkdir", "-p", final_dest.rsplit("/", 1)[0]])
            self.ssh_service.run(target, ["mv", incoming, final_dest])
            self.update_record(transfer_id, status="completed", completed_at=self._timestamp())
            return {"transfer_id": transfer_id, "status": "completed", "destination": final_dest}
        except TransferError as exc:
            self.update_record(transfer_id, status="failed", completed_at=self._timestamp(), error_code=exc.code, error_message=exc.message)
            try:
                self.ssh_service.run(target, ["rm", "-rf", incoming])
            except Exception:
                pass
            raise
