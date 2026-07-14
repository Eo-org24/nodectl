"""G1 security floor: legacy infra-reach paths (factory action route,
virsh/node.yaml SSH reads, terminal WS stub) must stay confined to their
current standalone entry points and never gain a caller under a future
port/adapter seam (roadmap §4A "Fence infra paths"; UCC-Standards §13, §15).

There are no ports yet in this repo (G3 not started); this test is a
regression guard so the moment a `ports/`/`adapters/` module appears and
imports one of these fenced symbols, the suite fails loudly instead of the
seam quietly growing a trusted-path shell/hypervisor dependency.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# symbol -> files allowed to reference it (definition site + known standalone callers)
FENCED_SYMBOLS = {
    "run_factory_script": {
        REPO_ROOT / "backend" / "ssh_client.py",
        REPO_ROOT / "backend" / "routers" / "api.py",
    },
    "get_virsh_list": {
        REPO_ROOT / "backend" / "ssh_client.py",
        REPO_ROOT / "backend" / "routers" / "api.py",
    },
    "get_node_manifests": {
        REPO_ROOT / "backend" / "ssh_client.py",
        REPO_ROOT / "backend" / "routers" / "api.py",
    },
    "hypervisor_snapshot": {
        REPO_ROOT / "backend" / "services" / "factory.py",
        REPO_ROOT / "backend" / "routers" / "api.py",
        REPO_ROOT / "backend" / "routers" / "ui.py",
    },
}

# Directories excluded by path *prefix* relative to REPO_ROOT (not by bare
# name-anywhere-in-path — REPO_ROOT itself is named "nodectl", and a naive
# `"nodectl" in path.parts` check would match every file in the repo and
# silently exclude everything).
EXCLUDED_PATH_PREFIXES = ("__pycache__", ".venv", "node_modules", "frontend", "nodectl", "tests")


def _python_files():
    for path in REPO_ROOT.rglob("*.py"):
        rel_parts = path.relative_to(REPO_ROOT).parts
        if any(part in {"__pycache__", ".venv"} for part in rel_parts):
            continue
        if rel_parts[0] in EXCLUDED_PATH_PREFIXES:
            continue
        yield path


def test_fenced_infra_symbols_have_no_new_callers():
    offenders = []
    for symbol, allowed_files in FENCED_SYMBOLS.items():
        pattern = re.compile(rf"\b{re.escape(symbol)}\b")
        for path in _python_files():
            if path in allowed_files:
                continue
            text = path.read_text(encoding="utf-8")
            if pattern.search(text):
                offenders.append(f"{symbol} referenced from {path.relative_to(REPO_ROOT)}")
    assert not offenders, (
        "Fenced standalone-only infra symbol(s) gained a new caller outside "
        f"their allowed standalone entry points: {offenders}. If this is a "
        "new FactoryPort/ArtifactPort adapter, route through the typed port "
        "contract instead of these legacy SSH/virsh/action paths."
    )


def test_no_port_or_adapter_module_exists_yet_touching_infra():
    """Sanity companion: once ports/adapters land, extend FENCED_SYMBOLS'
    allowed-file sets deliberately rather than letting this test go silent."""
    candidate_dirs = [REPO_ROOT / "backend" / "ports", REPO_ROOT / "backend" / "adapters"]
    existing = [d for d in candidate_dirs if d.exists()]
    if existing:
        raise AssertionError(
            f"Port/adapter directories now exist ({existing}) — review "
            "test_fenced_infra_symbols_have_no_new_callers' allowed-file sets "
            "before relying on this guard."
        )
