from __future__ import annotations

from ucc_contracts import validate_document

from backend import diagnostics


def test_effective_config_redacts_secret_fields(app_settings):
    dumped = diagnostics.effective_config(app_settings)

    assert dumped["secret_key"] == "[REDACTED]"
    assert dumped["admin_password"] == "[REDACTED]"
    assert dumped["viewer_password"] == "[REDACTED]"


def test_effective_config_never_leaks_the_real_secret_value(app_settings):
    dumped = diagnostics.effective_config(app_settings)

    serialized = " ".join(str(v) for v in dumped.values())
    assert app_settings.secret_key not in serialized
    assert app_settings.admin_password not in serialized


def test_effective_config_still_shows_non_secret_fields(app_settings):
    dumped = diagnostics.effective_config(app_settings)

    assert dumped["bind_port"] == app_settings.bind_port
    assert dumped["data_root"] == str(app_settings.data_root)


def test_module_health_validates_against_ucc_contracts_schema(app_settings):
    health = diagnostics.module_health(app_settings)

    validate_document("module-health", health)  # raises on schema violation
    assert health["module_id"] == "ucc"
    assert health["health"] == "healthy"


def test_module_health_reports_unavailable_when_runtime_is_broken(app_settings):
    app_settings.mock_ssh = False
    app_settings.factory_ssh_key_path.unlink()

    health = diagnostics.module_health(app_settings)

    validate_document("module-health", health)
    assert health["health"] == "unavailable"
