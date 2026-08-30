#!/usr/bin/env bash
# Smoke test for rootless Podman / Docker deployment (S2-D)
#
# Fail-closed: if a container engine is present, the container MUST actually
# build and come up, or this script fails loudly. It only degrades to the
# in-process import check when no container engine exists at all — never as
# a fallback for a real build/runtime failure.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== UCC Rootless Container Smoke Test (S2-D) ==="
echo "1. Validating container configuration..."
test -f Containerfile || test -f Dockerfile
test -f docker-compose.yml

echo "2. Checking read-only rootfs and tmpfs configuration in compose..."
grep -q "read_only: true" docker-compose.yml
grep -q "tmpfs:" docker-compose.yml
grep -q "UCC_EVENTS_ROOT" docker-compose.yml

echo "3. Testing container build and runtime (if Podman or Docker available)..."
CONTAINER_ENGINE=""
if command -v podman >/dev/null 2>&1; then
    CONTAINER_ENGINE="podman"
elif command -v docker >/dev/null 2>&1; then
    CONTAINER_ENGINE="docker"
fi

if [ -n "$CONTAINER_ENGINE" ]; then
    echo "Found container engine: $CONTAINER_ENGINE"

    CREATED_ENV=0
    CREATED_SECRETS=0
    HOST_PORT="${NODEPANEL_HOST_PORT:-8000}"

    if [ ! -f .env ]; then
        cp .env.example .env
        # Placeholder creds valid only for this throwaway smoke-test container.
        sed -i.bak \
            -e "s/^SECRET_KEY=.*/SECRET_KEY=smoke-test-secret-key/" \
            -e "s/^ADMIN_PASSWORD=.*/ADMIN_PASSWORD=smoke-test-password/" \
            -e "s/^VIEWER_PASSWORD=.*/VIEWER_PASSWORD=smoke-test-password/" \
            .env
        rm -f .env.bak
        CREATED_ENV=1
    fi

    mkdir -p secrets
    if [ ! -f secrets/factory_ssh_key ]; then
        ssh-keygen -t ed25519 -N "" -f secrets/factory_ssh_key -q
        CREATED_SECRETS=1
    fi
    if [ ! -f secrets/vm_ssh_key ]; then
        ssh-keygen -t ed25519 -N "" -f secrets/vm_ssh_key -q
        CREATED_SECRETS=1
    fi

    cleanup() {
        "$CONTAINER_ENGINE" compose down >/dev/null 2>&1 || true
        if [ "$CREATED_ENV" -eq 1 ]; then rm -f .env; fi
        if [ "$CREATED_SECRETS" -eq 1 ]; then rm -rf secrets; fi
        # Bind-mounted data dirs get chowned to the container's mapped UID;
        # remove them through the same user namespace so it's actually possible.
        if [ "$CONTAINER_ENGINE" = "podman" ]; then
            podman unshare rm -rf data staging inbox ledger events 2>/dev/null || true
        else
            rm -rf data staging inbox ledger events 2>/dev/null || true
        fi
    }
    trap cleanup EXIT

    # Remove any pre-existing image under this tag first: some compose
    # wrappers (podman-compose 1.0.6) do not propagate a failed build's exit
    # status through `up --build` and will silently start a stale image
    # instead of failing. Building and checking the exit code as its own
    # step, with nothing stale left to fall back to, closes that gap.
    "$CONTAINER_ENGINE" rmi -f "localhost/ucc-nodectl_nodepanel:latest" >/dev/null 2>&1 || true

    echo "Building via $CONTAINER_ENGINE compose..."
    if ! "$CONTAINER_ENGINE" compose build; then
        echo "FAIL: container build failed." >&2
        exit 1
    fi
    if ! "$CONTAINER_ENGINE" image inspect "localhost/ucc-nodectl_nodepanel:latest" >/dev/null 2>&1; then
        echo "FAIL: build reported success but no image was produced." >&2
        exit 1
    fi

    echo "Starting via $CONTAINER_ENGINE compose..."
    "$CONTAINER_ENGINE" compose up -d

    echo "Polling http://127.0.0.1:${HOST_PORT}/healthz ..."
    ok=0
    for _ in $(seq 1 20); do
        if curl -sf "http://127.0.0.1:${HOST_PORT}/healthz" >/dev/null 2>&1; then
            ok=1
            break
        fi
        sleep 1
    done
    if [ "$ok" -ne 1 ]; then
        echo "FAIL: /healthz did not respond. Container logs:" >&2
        "$CONTAINER_ENGINE" compose logs >&2 || true
        exit 1
    fi
    echo "Health check passed."

    echo "Container runtime test succeeded."
    cleanup
    trap - EXIT
else
    echo "No container engine (podman/docker) available in current environment; skipping live container test."
fi

echo "4. Testing in-process application entrypoint and imports..."
PY_BIN="$(which python3)"
if [ -f "../clones/nodectl/.venv/bin/python3" ]; then
    PY_BIN="../clones/nodectl/.venv/bin/python3"
fi

PYTHONPATH=.:third_party/ucc-contracts "$PY_BIN" -c '
from backend.app import create_app
from backend.catalog import CommandCatalog
from backend.projection import init_projection_db
app = create_app()
print("FastAPI app initialized successfully for rootless deployment.")
'

echo "=== Smoke test passed successfully! ==="
