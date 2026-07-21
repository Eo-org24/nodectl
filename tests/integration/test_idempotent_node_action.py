"""M-b: X-Idempotency-Key on POST /api/nodes/{node_name}/action/{action} —
the §5 idempotent-replay and idempotency-conflict fixtures, wired against a
real nodectl operation."""
from __future__ import annotations

import asyncio
from fastapi.testclient import TestClient
import pytest

from backend.db import get_db
from backend.idempotent_node_action import OutcomeUnknownError, run_node_action_idempotent
from backend.security import sign_payload
from ucc_contracts import validate_document


def _admin_client(app, app_settings) -> TestClient:
    client = TestClient(app=app)
    session = sign_payload(
        {"sub": "admin", "role": "admin", "csrf": "csrf-token", "terminal_target": "factory"},
        app_settings.secret_key,
    )
    client.cookies.set(app_settings.session_cookie_name, session)
    return client


def _post(client, app_settings, node_name, action, idempotency_key=None):
    headers = {app_settings.csrf_header_name: "csrf-token"}
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key
    return client.post(f"/api/nodes/{node_name}/action/{action}", headers=headers)


def test_new_key_proceeds_normally(app, app_settings):
    client = _admin_client(app, app_settings)
    response = _post(client, app_settings, "w-01", "snapshot", idempotency_key="k1")
    assert response.status_code == 200


def test_identical_replay_returns_200_without_rerunning(app, app_settings):
    client = _admin_client(app, app_settings)

    first = _post(client, app_settings, "w-01", "snapshot", idempotency_key="k1")
    second = _post(client, app_settings, "w-01", "snapshot", idempotency_key="k1")

    assert first.status_code == 200
    assert second.status_code == 200
    # replay must not append a second ledger entry or ucc.event
    ledger_file = next(app_settings.ledger_root.glob("*.jsonl"))
    ledger_lines = [l for l in ledger_file.read_text(encoding="utf-8").splitlines() if l]
    assert len(ledger_lines) == 1
    event_lines = [
        line for line in (app_settings.ucc_events_root / "ucc.jsonl")
        .read_text(encoding="utf-8").splitlines() if line
    ]
    assert len(event_lines) == 1


def test_same_key_different_action_is_a_conflict(app, app_settings):
    client = _admin_client(app, app_settings)

    _post(client, app_settings, "w-01", "snapshot", idempotency_key="k1")
    response = _post(client, app_settings, "w-01", "destroy", idempotency_key="k1")

    assert response.status_code == 409


def test_no_header_keeps_legacy_behavior(app, app_settings):
    client = _admin_client(app, app_settings)

    first = _post(client, app_settings, "w-01", "snapshot")
    second = _post(client, app_settings, "w-01", "snapshot")

    assert first.status_code == 200
    assert second.status_code == 200
    # no idempotency key => every call is logged, unlike the replay case
    ledger_file = next(app_settings.ledger_root.glob("*.jsonl"))
    ledger_lines = [l for l in ledger_file.read_text(encoding="utf-8").splitlines() if l]
    assert len(ledger_lines) == 2


def test_stored_result_is_a_validated_ucc_result(app, app_settings):
    import sqlite3
    import json

    client = _admin_client(app, app_settings)
    _post(client, app_settings, "w-01", "snapshot", idempotency_key="k1")

    conn = sqlite3.connect(app_settings.database_path)
    row = conn.execute(
        "SELECT result_json FROM idempotency_records WHERE idempotency_key = ?", ("k1",)
    ).fetchone()
    conn.close()
    assert row is not None
    stored_value = json.loads(row[0])
    validate_document("result", stored_value["result"])


def test_ambiguous_dispatch_is_not_reexecuted(app, monkeypatch):
    calls = 0

    async def ambiguous_dispatch(*, node_name, action):
        nonlocal calls
        calls += 1
        raise RuntimeError("connection dropped after dispatch")

    monkeypatch.setattr(
        "backend.idempotent_node_action.run_factory_script", ambiguous_dispatch,
    )
    with get_db() as conn:
        with pytest.raises(RuntimeError):
            asyncio.run(run_node_action_idempotent(
                conn, node_name="w-01", action="destroy",
                idempotency_key="ambiguous-k", actor_username="admin",
            ))
        with pytest.raises(OutcomeUnknownError) as exc_info:
            asyncio.run(run_node_action_idempotent(
                conn, node_name="w-01", action="destroy",
                idempotency_key="ambiguous-k", actor_username="admin",
            ))

    assert calls == 1
    assert exc_info.value.problem["code"] == "outcome_unknown"
    validate_document("problem", exc_info.value.problem)
