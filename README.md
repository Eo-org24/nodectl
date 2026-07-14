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

## Additional Documentation

- [Deployment](docs/DEPLOYMENT.md)
- [SSH host-key enrollment](docs/SSH_HOST_KEYS.md)
- [Git deploy keys](docs/GIT_DEPLOY_KEYS.md)
