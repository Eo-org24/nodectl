from __future__ import annotations

import pytest

from backend.config import Settings


def test_validate_runtime_requires_ssh_keys_when_not_mocked(app_settings):
    app_settings.mock_ssh = False
    app_settings.factory_ssh_key_path.unlink()

    with pytest.raises(RuntimeError, match="Missing SSH key file"):
        app_settings.validate_runtime()


def test_unconfigured_defaults_isolate_under_dev_root(monkeypatch):
    # M-c: an ad-hoc local run with no .env / no explicit env vars must not
    # scatter data/staging/inbox/ledger/events/db loose into the repo root —
    # everything lands under one git-ignored .ucc-dev/ instead. Deployed
    # environments (docker-compose, tests) always override every one of
    # these explicitly, so this only exercises the bare default.
    for var in ("DATA_ROOT", "STAGING_ROOT", "INBOX_ROOT", "LEDGER_ROOT",
                "UCC_EVENTS_ROOT", "DATABASE_PATH", "SSH_KNOWN_HOSTS_PATH"):
        monkeypatch.delenv(var, raising=False)
    defaults = Settings(_env_file=None)

    assert str(defaults.data_root).startswith(".ucc-dev")
    assert str(defaults.staging_root).startswith(".ucc-dev")
    assert str(defaults.inbox_root).startswith(".ucc-dev")
    assert str(defaults.ledger_root).startswith(".ucc-dev")
    assert str(defaults.ucc_events_root).startswith(".ucc-dev")
    assert str(defaults.database_path).startswith(".ucc-dev")
    assert str(defaults.ssh_known_hosts_path).startswith(".ucc-dev")


def test_app_settings_fixture_uses_an_isolated_tmp_root_not_dev_root(app_settings, tmp_path):
    # Locks in that tests never touch the real .ucc-dev/ dev root or repo
    # root — the app_settings fixture (conftest.py) points every root at
    # tmp_path instead.
    assert str(app_settings.data_root).startswith(str(tmp_path))
    assert ".ucc-dev" not in str(app_settings.data_root)
