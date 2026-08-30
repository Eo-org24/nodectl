"""XDG logical path resolver for UCC (Standards Reference §17).

Provides standard resolution of configuration, data, state, and runtime paths
using environment variables (XDG_CONFIG_HOME, XDG_DATA_HOME, XDG_STATE_HOME,
XDG_RUNTIME_DIR) with fallback to local development roots.
"""
from __future__ import annotations

import os
from pathlib import Path


def get_xdg_config_home(app_name: str = "ucc") -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / app_name
    return Path.home() / ".config" / app_name


def get_xdg_data_home(app_name: str = "ucc") -> Path:
    base = os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base) / app_name
    return Path.home() / ".local" / "share" / app_name


def get_xdg_state_home(app_name: str = "ucc") -> Path:
    base = os.environ.get("XDG_STATE_HOME")
    if base:
        return Path(base) / app_name
    return Path.home() / ".local" / "state" / app_name


def get_xdg_runtime_dir(app_name: str = "ucc") -> Path:
    base = os.environ.get("XDG_RUNTIME_DIR")
    if base:
        return Path(base) / app_name
    return Path(f"/tmp/ucc-runtime-{os.getuid() if hasattr(os, "getuid") else "user"}")


class XDGPathResolver:
    def __init__(self, app_name: str = "ucc"):
        self.app_name = app_name

    @property
    def config_dir(self) -> Path:
        p = get_xdg_config_home(self.app_name)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def data_dir(self) -> Path:
        p = get_xdg_data_home(self.app_name)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def state_dir(self) -> Path:
        p = get_xdg_state_home(self.app_name)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def runtime_dir(self) -> Path:
        p = get_xdg_runtime_dir(self.app_name)
        p.mkdir(parents=True, exist_ok=True)
        return p
