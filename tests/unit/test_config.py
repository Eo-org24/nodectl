from __future__ import annotations

import pytest


def test_validate_runtime_requires_ssh_keys_when_not_mocked(app_settings):
    app_settings.mock_ssh = False
    app_settings.factory_ssh_key_path.unlink()

    with pytest.raises(RuntimeError, match="Missing SSH key file"):
        app_settings.validate_runtime()
