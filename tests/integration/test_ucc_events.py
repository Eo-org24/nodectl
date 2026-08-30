"""G2 dual-write: POST /api/nodes/{node_name}/action/{action} also appends a
schema-conformant ucc.event alongside the legacy Ledger.write() entry."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

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


def _read_ucc_events(app_settings) -> list[dict]:
    events_path = app_settings.ucc_events_root / "ucc.jsonl"
    if not events_path.exists():
        return []
    lines = [l for l in events_path.read_text(encoding="utf-8").splitlines() if l]
    return [json.loads(l) for l in lines]


def test_node_action_dual_writes_conformant_ucc_event(app, app_settings):
    client = _admin_client(app, app_settings)

    response = client.post(
        "/api/nodes/w-01/action/snapshot",
        headers={app_settings.csrf_header_name: "csrf-token"},
    )
    assert response.status_code == 200

    events = _read_ucc_events(app_settings)
    assert len(events) == 1
    validate_document("event", events[0])
    assert events[0]["event_type"] == "node.snapshot_completed"
    assert events[0]["producer"]["module_id"] == "ucc"


def test_node_action_legacy_ledger_still_written_alongside(app, app_settings):
    client = _admin_client(app, app_settings)

    client.post(
        "/api/nodes/w-01/action/snapshot",
        headers={app_settings.csrf_header_name: "csrf-token"},
    )

    ledger_file = next(app_settings.ledger_root.glob("*.jsonl"))
    assert ledger_file.read_text(encoding="utf-8").strip() != ""
    assert len(_read_ucc_events(app_settings)) == 1


def test_same_node_correlates_across_events(app, app_settings):
    client = _admin_client(app, app_settings)

    client.post("/api/nodes/w-01/action/snapshot", headers={app_settings.csrf_header_name: "csrf-token"})
    client.post("/api/nodes/w-01/action/snapshot", headers={app_settings.csrf_header_name: "csrf-token"})

    events = _read_ucc_events(app_settings)
    assert len(events) == 2
    assert events[0]["subject"]["id"].startswith("node_")
    assert events[1]["subject"]["id"].startswith("node_")
    assert events[0]["producer_sequence"] == 0
    assert events[1]["producer_sequence"] == 1
