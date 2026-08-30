"""Unit tests for S2-4: Disposable Projection DB & Event Stream Projection Builder."""
from pathlib import Path
import json
import sqlite3
import pytest

from backend.db import get_db, init_db
from backend.projection import (
    apply_event_to_projection,
    build_projection,
    get_projection_db,
    init_projection_db,
    load_events_from_streams,
    rebuild_projection,
)
from ucc_contracts import new_id


def test_projection_db_builds_from_events(tmp_path):
    events_file = tmp_path / "ucc.jsonl"
    events = [
        {
            "schema": "ucc.event",
            "schema_version": 1,
            "event_id": new_id("evt"),
            "event_type": "allocation_reserved",
            "occurred_at": "2026-08-22T12:00:00.000Z",
            "recorded_at": "2026-08-22T12:00:00.000Z",
            "producer": {"module_id": "vm-factory", "instance_id": new_id("act")},
            "actor": {"kind": "human", "id": new_id("act")},
            "subject": {"kind": "node", "id": "node_01M0NW6TX9RXWAFGQ71WS63001"},
            "operation_id": new_id("op"),
            "request_id": new_id("req"),
            "correlation_id": new_id("corr"),
            "producer_sequence": 0,
            "payload": {"node_name": "worker-1", "allocation_id": "nalloc_01M0NW6TX9RXWAFGQ71WS63001"},
        },
        {
            "schema": "ucc.event",
            "schema_version": 1,
            "event_id": new_id("evt"),
            "event_type": "node_quarantined",
            "occurred_at": "2026-08-22T12:05:00.000Z",
            "recorded_at": "2026-08-22T12:05:00.000Z",
            "producer": {"module_id": "vm-factory", "instance_id": new_id("act")},
            "actor": {"kind": "human", "id": new_id("act")},
            "subject": {"kind": "node", "id": "node_01M0NW6TX9RXWAFGQ71WS63001"},
            "operation_id": new_id("op"),
            "request_id": new_id("req"),
            "correlation_id": new_id("corr"),
            "producer_sequence": 1,
            "payload": {"node_name": "worker-1", "reason": "Lease cleanup failed"},
        },
    ]
    with open(events_file, "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

    proj_db = tmp_path / "projection.db"
    count = build_projection([events_file], proj_db)
    assert count == 2

    with get_projection_db(proj_db) as conn:
        node = conn.execute("SELECT * FROM projected_nodes WHERE node_id = ?", ("node_01M0NW6TX9RXWAFGQ71WS63001",)).fetchone()
        assert node is not None
        assert node["display_name"] == "worker-1"
        assert node["quarantine_state"] == "quarantined"
        assert node["readiness"] == "quarantined"

        quarantine = conn.execute("SELECT * FROM projected_quarantines WHERE node_id = ?", ("node_01M0NW6TX9RXWAFGQ71WS63001",)).fetchone()
        assert quarantine is not None
        assert quarantine["reason"] == "Lease cleanup failed"


def test_byte_stable_projection_rebuild_and_canonical_journal_survival(tmp_path):
    # Setup canonical DB (journal.db / nodepanel.db) with real migration records
    journal_db = tmp_path / "journal.db"
    init_db(journal_db)
    with get_db(journal_db) as conn:
        conn.execute(
            "INSERT INTO idempotency_records (idempotency_key, request_fingerprint, operation_type, disposition, result_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("key-1", "sha256:abcd", "node.action", "completed", "{}", "2026-08-22T12:00:00Z"),
        )

    # Verify canonical record exists
    with get_db(journal_db) as conn:
        row = conn.execute("SELECT * FROM idempotency_records WHERE idempotency_key = ?", ("key-1",)).fetchone()
        assert row is not None

    events_file = tmp_path / "events.jsonl"
    events = [
        {
            "schema": "ucc.event",
            "schema_version": 1,
            "event_id": "evt_01M0NW6TX9RXWAFGQ71WS63E01",
            "event_type": "artifact_published",
            "occurred_at": "2026-08-22T12:00:00.000Z",
            "recorded_at": "2026-08-22T12:00:00.000Z",
            "producer": {"module_id": "artifact-compiler", "instance_id": "act_01M0NW6TX9RXWAFGQ71WS63A01"},
            "actor": {"kind": "human", "id": "act_01M0NW6TX9RXWAFGQ71WS63A01"},
            "subject": {"kind": "artifact", "id": "art_01M0NW6TX9RXWAFGQ71WS63R01"},
            "operation_id": "op_01M0NW6TX9RXWAFGQ71WS63O01",
            "request_id": "req_01M0NW6TX9RXWAFGQ71WS63Q01",
            "correlation_id": "corr_01M0NW6TX9RXWAFGQ71WS63C01",
            "producer_sequence": 0,
            "payload": {
                "name": "benchmark-runner",
                "status": "published",
                "revision_id": "rev_01M0NW6TX9RXWAFGQ71WS63R01",
                "content_hash": "sha256:" + "0" * 64,
            },
        }
    ]
    with open(events_file, "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

    proj_db = tmp_path / "projection.db"

    # 1. First build
    build_projection([events_file], proj_db)
    with get_projection_db(proj_db) as conn:
        rows1 = conn.execute("SELECT * FROM projected_artifacts ORDER BY artifact_id").fetchall()
        dump1 = [dict(r) for r in rows1]

    # 2. Rebuild projection from scratch
    rebuild_projection([events_file], proj_db)
    with get_projection_db(proj_db) as conn:
        rows2 = conn.execute("SELECT * FROM projected_artifacts ORDER BY artifact_id").fetchall()
        dump2 = [dict(r) for r in rows2]

    assert dump1 == dump2

    # 3. Canonical journal rows survive completely untouched
    with get_db(journal_db) as conn:
        canonical_row = conn.execute("SELECT * FROM idempotency_records WHERE idempotency_key = ?", ("key-1",)).fetchone()
        assert canonical_row is not None
        assert canonical_row["operation_type"] == "node.action"
