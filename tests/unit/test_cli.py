from __future__ import annotations

import json

from backend import cli


def test_config_show_prints_redacted_json(app_settings, capsys, monkeypatch):
    monkeypatch.setattr(cli, "settings", app_settings)
    monkeypatch.setattr("sys.argv", ["nodectl", "config", "show", "--effective", "--redacted"])

    assert cli.main() == 0
    out = json.loads(capsys.readouterr().out)
    assert out["secret_key"] == "[REDACTED]"


def test_module_health_prints_valid_record(app_settings, capsys, monkeypatch):
    monkeypatch.setattr(cli, "settings", app_settings)
    monkeypatch.setattr("sys.argv", ["nodectl", "module-health"])

    assert cli.main() == 0
    out = json.loads(capsys.readouterr().out)
    assert out["schema"] == "ucc.module-registration"
    assert out["module_id"] == "ucc"
