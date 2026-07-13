from __future__ import annotations

from pathlib import Path

import pytest

from backend.app import create_app
from backend.config import settings
from backend.db import init_db


@pytest.fixture()
def app_settings(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    staging_root = tmp_path / "staging"
    inbox_root = tmp_path / "inbox"
    ledger_root = tmp_path / "ledger"
    known_hosts = data_root / "known_hosts"
    attrs = {
        "secret_key": "test-secret-key",
        "admin_username": "admin",
        "admin_password": "admin-pass",
        "viewer_username": "viewer",
        "viewer_password": "viewer-pass",
        "data_root": data_root,
        "staging_root": staging_root,
        "inbox_root": inbox_root,
        "ledger_root": ledger_root,
        "database_path": data_root / "nodepanel.db",
        "ssh_known_hosts_path": known_hosts,
        "factory_ssh_key_path": tmp_path / "factory_key",
        "vm_ssh_key_path": tmp_path / "vm_key",
        "allowed_origins": ["http://testserver", "http://127.0.0.1:8000"],
        "github_known_hosts_entry": "github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFakeKeyValue",
        "mock_ssh": True,
        "secure_cookies": False,
        "ssh_use_agent": False,
    }
    for key, value in attrs.items():
        monkeypatch.setattr(settings, key, value)
    settings.ensure_directories()
    settings.factory_ssh_key_path.write_text("factory-key", encoding="utf-8")
    settings.vm_ssh_key_path.write_text("vm-key", encoding="utf-8")
    init_db()
    return settings


@pytest.fixture()
def app(app_settings):
    return create_app()
