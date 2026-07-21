# NodePanel

NodePanel is a FastAPI control plane for a homelab VM factory. The backend owns all control logic; the browser is a thin authenticated client for SSH-backed status, file transfer, Git deploy-key setup, and terminal access.

## Architecture

- `backend.main:app` is the Uvicorn entrypoint.
- `backend/app.py` builds the application and wires routers plus services.
- `backend/routers/` contains HTTP and WebSocket endpoints.
- `backend/services/` contains SSH, transfer, host-key, and Git deploy-key logic.
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
.venv/bin/python -m pytest -q
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

Conforms to **ucc-contracts v0.2.0** (git tag, ucc-contracts is now its own repo), vendored at
`third_party/ucc-contracts/` (schemas, lifecycle transition tables, ID/hash/path
primitives — no domain code). `tests/contracts/` asserts this repo's own
(de)serialization and validation matches the pinned contracts exactly;
bumping the vendored copy is deliberate and version-gated, never silent.

## Standalone status and limitations

This is a **UCC Stage-1 conformant standalone tool**. It runs and is tested on its own.
It is *not* the UCC product and does not integrate with the other UCC repos yet.

- **Shared contracts:** pinned to `ucc-contracts v0.2.0` (vendored under
  `third_party/ucc-contracts/`, export set per its VENDOR-MANIFEST.md). Never edited locally.
- **Placeholder entity IDs (D4):** `ucc.event` records carry `subject.id` values that are
  **deterministic sha256-derived placeholders**, not canonical prefixed ULIDs. Real IDs
  arrive with the record layer in Stage 2. **Do not build external references on them.**
- **Events are dual-written:** the legacy ledger *and* a schema-conformant `ucc.event`
  stream. Neither replaces the other yet.
- **`producer_sequence`** is per-producer, not globally ordered, and not race-safe under
  concurrent writers (matching the legacy ledgers).
- **Fenced paths:** direct-infrastructure and shell paths are retained for standalone use
  only, unreachable from any port (AST call-site tests). Not an integration surface.
- **Domain schemas are not authored yet** (~26 records; standards reference §17). They gate
  the vertical proof, not this baseline.
- **Ports are stubs.** `ArtifactPort`/`FactoryPort` are consumed at `app.state.*_port`, but
  every method refuses `DEPENDENCY_UNAVAILABLE` by design. No cross-module call is wired.
- **`nodepanel` naming survives by design** in the SQLite filename, the `factory_user`
  account, and `VALID_TOOL`'s legacy entry — a deliberate D5 transition window.

## Additional Documentation

- [Deployment](docs/DEPLOYMENT.md)
- [SSH host-key enrollment](docs/SSH_HOST_KEYS.md)
- [Git deploy keys](docs/GIT_DEPLOY_KEYS.md)
