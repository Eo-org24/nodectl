# Deployment

NodePanel is intended to run behind an authenticated reverse proxy or a private VPN boundary. When `network_mode: host` is enabled, Uvicorn binds to `127.0.0.1:8000` only; do not expose the container directly on a public interface.

## Persistent Paths

- `DATA_ROOT=/app/data`
- `STAGING_ROOT=/app/staging`
- `INBOX_ROOT=/app/inbox`
- `LEDGER_ROOT=/app/ledger`
- `DATABASE_PATH=/app/data/nodepanel.db`

## Secrets

- `./secrets/factory_ssh_key` is mounted as `/run/secrets/factory_ssh_key`
- `./secrets/vm_ssh_key` is mounted as `/run/secrets/vm_ssh_key`

## Login Accounts

Configure the built-in accounts through `.env`:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `VIEWER_USERNAME`
- `VIEWER_PASSWORD`

Do not mount the host `~/.ssh` directory. Populate `./data/known_hosts` with approved host keys through the NodePanel enrollment workflow or your configuration management pipeline.

## Reverse Proxy / VPN Boundary

1. Bind NodePanel to loopback only.
2. Place an authenticated reverse proxy, SSH tunnel, or VPN in front of it.
3. Terminate TLS at that boundary and include `http://127.0.0.1:8000` or the proxy origin in `ALLOWED_ORIGINS`.

## Runtime Commands

Build:

```bash
podman compose build
# fallback: docker compose build
```

Start:

```bash
podman compose up -d
# fallback: docker compose up -d
```

Verify:

```bash
.venv/bin/python - <<'PY'
import urllib.request
with urllib.request.urlopen("http://127.0.0.1:8000/healthz", timeout=5) as response:
    print(response.status, response.read().decode())
PY
python -m backend.cli ssh-diagnose --target factory
```
