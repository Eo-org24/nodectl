"""Read-only diagnostics (M-c): a redacted effective-config dump and a
`ucc.module-registration`-shaped health record, for `backend/cli.py`.

Both compute their answer from real, already-defined state — settings
defaults/overrides and the same startup check `lifespan()` runs in app.py —
never a fabricated or hardcoded-optimistic value (fail-closed, AGENTS.md §1.2).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import Settings
from .db import init_db

# Field names whose value must never be printed by a diagnostic surface,
# redacted regardless of --redacted (there is no un-redacted mode).
_SECRET_FIELDS = frozenset({"secret_key", "admin_password", "viewer_password"})

MODULE_ID = "ucc"
# No real release process exists yet for standalone nodectl (the fork-gate
# tag is still pending) — an honest, obviously-placeholder version rather
# than a fabricated semver, same convention as D4's placeholder subject IDs.
MODULE_VERSION = "0.0.0-standalone"


def effective_config(settings: Settings) -> dict[str, Any]:
    """The resolved (defaults + env + .env) settings, secrets redacted."""
    data: dict[str, Any] = {}
    for name, value in settings.model_dump().items():
        if name in _SECRET_FIELDS:
            data[name] = "[REDACTED]"
        elif isinstance(value, Path):
            data[name] = str(value)
        else:
            data[name] = value
    return data


def module_health(settings: Settings) -> dict[str, Any]:
    """A `ucc.module-registration`-shaped record (see
    third_party/ucc-contracts/schemas/module-health.schema.json). `health` is
    computed by running the exact same startup sequence app.py's lifespan
    does (ensure_directories -> validate_runtime -> init_db), not a separate
    guess at what "healthy" means."""
    health = "healthy"
    try:
        settings.ensure_directories()
        settings.validate_runtime()
        init_db()
    except Exception:
        health = "unavailable"
    return {
        "schema": "ucc.module-registration",
        "schema_version": 1,
        "module_id": MODULE_ID,
        "display_name": settings.app_name,
        "module_version": MODULE_VERSION,
        "adapter_kind": "http",
        "enabled": True,
        "supported_contract_versions": [1],
        # Stage 1: ports are refuse-only stubs (real adapters are Stage 2),
        # so nodectl offers no real inter-module capability yet — reporting
        # any would be exactly the fabrication AGENTS.md §1.2 forbids.
        "capabilities": [],
        "canonical_root": str(settings.data_root),
        "health_timeout_seconds": 5,
        "health": health,
    }
