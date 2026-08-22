#!/usr/bin/env bash
# Smoke test for rootless Podman / Docker deployment (S2-D)
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

echo "3. Testing container entrypoint syntax and imports..."
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
