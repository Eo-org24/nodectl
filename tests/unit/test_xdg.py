"""Unit tests for XDG path resolution."""
from pathlib import Path
from backend.xdg import XDGPathResolver, get_xdg_config_home, get_xdg_data_home, get_xdg_state_home


def test_xdg_resolution_respects_env(monkeypatch, tmp_path):
    config_dir = tmp_path / "custom_config"
    data_dir = tmp_path / "custom_data"
    state_dir = tmp_path / "custom_state"

    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_dir))

    resolver = XDGPathResolver("ucc-test")
    assert resolver.config_dir == config_dir / "ucc-test"
    assert resolver.data_dir == data_dir / "ucc-test"
    assert resolver.state_dir == state_dir / "ucc-test"
    assert (config_dir / "ucc-test").exists()
