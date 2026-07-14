"""G1 security floor: legacy infra-reach paths (factory action route,
virsh/node.yaml SSH reads, terminal WS stub) must stay confined to their
current standalone entry points and never gain a caller under a future
port/adapter seam (roadmap §4A "Fence infra paths"; UCC-Standards §13, §15).

There are no ports yet in this repo (G3 not started); this test is a
regression guard so the moment a `ports`/`adapters` module appears and
calls one of these fenced symbols, the suite fails loudly instead of the
seam quietly growing a trusted-path shell/hypervisor dependency.

Uses AST call-site detection, not text/regex matching: an earlier version
matched the bare symbol name anywhere in a file's text, which will false-
positive the moment a port module's own docstring documents the fence it
respects (as backend/ports/*.py's do from G3 onward). Only actual call
expressions — `symbol(...)` or `x.symbol(...)` — count.
"""
from __future__ import annotations

import ast
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


def _called_names(path: Path) -> set[str]:
    """Every identifier actually invoked as a call in this file: bare
    `name(...)` and attribute `x.name(...)` forms both count."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    return names


def test_fenced_infra_symbols_have_no_new_callers():
    offenders = []
    for symbol, allowed_files in FENCED_SYMBOLS.items():
        for path in _python_files():
            if path in allowed_files:
                continue
            if symbol in _called_names(path):
                offenders.append(f"{symbol} referenced from {path.relative_to(REPO_ROOT)}")
    assert not offenders, (
        "Fenced standalone-only infra symbol(s) gained a new caller outside "
        f"their allowed standalone entry points: {offenders}. If this is a "
        "new FactoryPort/ArtifactPort adapter, route through the typed port "
        "contract instead of these legacy SSH/virsh/action paths."
    )


def test_port_stubs_touch_none_of_the_fenced_infra_symbols():
    """G3 landed backend/ports/ (ArtifactPort/FactoryPort stubs, roadmap
    §4A). This replaces the earlier G1-era canary that asserted no
    ports/adapters directory existed yet — that assertion's job is done now
    that ports exist deliberately; what still matters is that the stubs
    (and any future real adapter dropped in alongside them) call none of
    the fenced symbols above. FENCED_SYMBOLS' allowed-file sets were
    reviewed when backend/ports/ landed and intentionally were not
    extended to include it."""
    ports_dir = REPO_ROOT / "backend" / "ports"
    assert ports_dir.exists(), "backend/ports/ is expected from G3 onward"
    port_files = [p for p in ports_dir.glob("*.py")]
    assert port_files, "backend/ports/ exists but has no stub modules"
    fenced = set(FENCED_SYMBOLS)
    for path in port_files:
        touched = _called_names(path) & fenced
        assert not touched, f"{path.relative_to(REPO_ROOT)} calls fenced symbol(s): {touched}"
