# NodePanel

NodePanel is a FastAPI control plane for a homelab VM factory. The backend owns all control logic; the browser is a thin authenticated client for SSH-backed status, file transfer, Git deploy-key setup, and terminal access.

## UCC integration lineage

This is the UCC Stage 2 integration line, cut from
`Eowerd24/nodectl@nodectl-phase0-conformant-standalone-v2`
(`09783571754cfb21818115707fb99be833e34919`). The upstream `Eowerd24/nodectl` line is the
frozen standalone baseline and receives no Stage 2 commits.

Pinned peers:

- `Eowerd24/Artifact-compiler@phase0-conformant-v2`
  (`ad3753980b4510d755435571b28fb11bb434ab9a`)
- `Eowerd24/VM-Factory@phase0-conformant-v2`
  (`4f8f577364fb2b2b3a17e780fa7cc7a601058d0d`)
- shared contracts: `Eowerd24/ucc-contracts@v0.3.0`

UCC work and pull requests target `Eo-org24/nodectl:ucc-integration`. The preserved
`ucc-integration-premature-stage2` branch was based on void pre-reconciliation tags and is
audit evidence only; do not merge or cherry-pick it.

## Architecture

- `backend.main:app` is the Uvicorn entrypoint.
- `backend/app.py` builds the application and wires routers plus services.
- `backend/routers/` contains HTTP and WebSocket endpoints.
- `backend/services/` contains SSH, transfer, host-key, and Git deploy-key logic.
- `backend/ports/` contains real in-process adapters for `ArtifactPort` and `FactoryPort`.
- `backend/projection.py` builds the disposable projection DB from event streams.
- `backend/migrations/001_init.sql` creates the SQLite tables for transfer records, approved host keys, and Git credential metadata.

## Security Defaults

- Cookie-based authentication with `admin` and `viewer` roles.
- The login accounts are configured through `.env`, not through a browser signup flow.
- CSRF protection for browser mutation requests.
- WebSocket origin checks and authenticated session binding.
- Paramiko `RejectPolicy` with a dedicated `known_hosts` file.
- Separate injected SSH secrets for factory and VM access.
- No host `~/.ssh` mount.
- No private keys or tokens stored in SQLite or rendered back to the browser.

## Commands

Build Python bytecode check:

```bash
.venv/bin/python -m compileall backend tests
```

Run tests:

```bash
PYTHONPATH=.:third_party/ucc-contracts pytest -q
```

Run the app locally:

```bash
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Build the container:

```bash
podman compose build
# fallback: docker compose build
```

Start the container:

```bash
podman compose up -d
# fallback: docker compose up -d
```

Verify health:

```bash
.venv/bin/python - <<'PY'
import urllib.request
with urllib.request.urlopen("http://127.0.0.1:8000/healthz", timeout=5) as response:
    print(response.status, response.read().decode())
PY
python -m backend.cli ssh-diagnose --target factory
```

## User Accounts

Set users in `.env`:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `VIEWER_USERNAME`
- `VIEWER_PASSWORD`

The current backend maps those two configured accounts to roles in [`backend/auth.py`](backend/auth.py).

## UCC conformance

Conforms to **ucc-contracts v0.3.0** (git tag, ucc-contracts is now its own repo), vendored at
`third_party/ucc-contracts/` (schemas, lifecycle transition tables, ID/hash/path
primitives — no domain code). `tests/contracts/` asserts this repo's own
(de)serialization and validation matches the pinned contracts exactly;
bumping the vendored copy is deliberate and version-gated, never silent.

## Stage-2 Integration Status

- **Shared contracts:** pinned to `ucc-contracts v0.3.0` (vendored under
  `third_party/ucc-contracts/`, export set per its VENDOR-MANIFEST.md).
- **Canonical entity IDs (S2-5):** `ucc.event` records carry genuine owner-issued
  canonical ULIDs (`act_`, `node_`, `op_`, etc.).
- **Authoritative event stream (S2-6):** `ucc.event` stream is the authoritative write path.
- **Disposable projection DB (S2-4):** rebuildable deterministically from event streams.
- **Ports:** in-process adapters for `ArtifactPort` and `FactoryPort` wired at `app.state.*_port`.
- **Rootless Container (S2-D):** Containerfile and docker-compose.yml support unprivileged execution.

## Additional Documentation

- [Deployment](docs/DEPLOYMENT.md)
- [SSH host-key enrollment](docs/SSH_HOST_KEYS.md)
- [Git deploy keys](docs/GIT_DEPLOY_KEYS.md)
