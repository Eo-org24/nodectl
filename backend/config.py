from __future__ import annotations

import getpass
import secrets
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "NodePanel"
    environment: str = "development"
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    session_cookie_name: str = "nodepanel_session"
    session_max_age_seconds: int = 60 * 60 * 8
    csrf_header_name: str = "X-CSRF-Token"
    secure_cookies: bool = False

    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://127.0.0.1:8000", "http://localhost:8000"])

    admin_username: str = Field(default_factory=getpass.getuser)
    admin_password: str = "change-me-now"
    viewer_username: str = "viewer"
    viewer_password: str = "change-me-viewer"

    data_root: Path = Path("data")
    staging_root: Path = Path("staging")
    inbox_root: Path = Path("inbox")
    ledger_root: Path = Path("ledger")
    ucc_events_root: Path = Path("events")
    database_path: Path = Path("data/nodepanel.db")

    factory_host: str = "127.0.0.1"
    factory_port: int = 22
    factory_user: str = "nodepanel"
    factory_dir: str = "~/nodefactory"
    factory_ssh_key_path: Path = Path("secrets/factory_ssh_key")

    vm_ssh_key_path: Path = Path("secrets/vm_ssh_key")
    ssh_known_hosts_path: Path = Path("data/known_hosts")
    ssh_use_agent: bool = False
    ssh_connect_timeout_seconds: int = 10

    github_known_hosts_entry: str = ""

    max_transfer_bytes: int = 1024 * 1024 * 1024
    max_transfer_files: int = 5000
    max_individual_file_bytes: int = 128 * 1024 * 1024
    transfer_timeout_seconds: int = 600

    mock_ssh: bool = False

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def ensure_directories(self) -> None:
        for path in (self.data_root, self.staging_root, self.inbox_root, self.ledger_root, self.ucc_events_root):
            path.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.ssh_known_hosts_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.ssh_known_hosts_path.exists():
            self.ssh_known_hosts_path.touch(mode=0o600)

    def validate_runtime(self) -> None:
        required_paths = [
            self.data_root,
            self.staging_root,
            self.inbox_root,
            self.ledger_root,
            self.database_path.parent,
            self.ssh_known_hosts_path.parent,
        ]
        for path in required_paths:
            if not path.exists():
                raise RuntimeError(f"Required path does not exist: {path}")
            if not path.is_dir():
                raise RuntimeError(f"Required path is not a directory: {path}")
        if not self.mock_ssh:
            for key_path in (self.factory_ssh_key_path, self.vm_ssh_key_path):
                if not key_path.exists():
                    raise RuntimeError(f"Missing SSH key file: {key_path}")
                if not key_path.is_file():
                    raise RuntimeError(f"SSH key path is not a file: {key_path}")
        self._assert_writable(self.database_path.parent, "database directory")
        self._assert_writable(self.ssh_known_hosts_path.parent, "known_hosts directory")

    @staticmethod
    def _assert_writable(path: Path, label: str) -> None:
        probe = path / ".nodepanel-write-probe"
        try:
            probe.write_text("ok", encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"{label} is not writable: {path}") from exc
        finally:
            probe.unlink(missing_ok=True)


settings = Settings()
