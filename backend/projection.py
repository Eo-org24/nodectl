"""Disposable Projection DB and Event Stream Projection Builder (S2-4).

Projection DB (<state_dir>/projection.db) is entirely disposable and can be
rebuilt deterministically from the three UCC event streams:
- nodectl / events / ucc.jsonl
- artifact-compiler / events / artifact-compiler.jsonl
- vm-factory / events / vm-factory.jsonl

The canonical journal DB (<state_dir>/nodepanel.db or journal.db) holds
authoritative write state and idempotency records and is never mutated by
projection rebuilds.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from .config import settings


def now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


PROJECTION_SCHEMA = """
CREATE TABLE IF NOT EXISTS projected_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    producer_module TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    producer_sequence INTEGER NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projected_nodes (
    node_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    provider_kind TEXT NOT NULL DEFAULT 'mock',
    runtime_state TEXT NOT NULL DEFAULT 'running',
    readiness TEXT NOT NULL DEFAULT 'ready',
    allocation_phase TEXT NOT NULL DEFAULT 'unallocated',
    health TEXT NOT NULL DEFAULT 'healthy',
    quarantine_state TEXT NOT NULL DEFAULT 'not_quarantined',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projected_artifacts (
    artifact_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    latest_revision_id TEXT,
    latest_hash TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projected_executions (
    execution_id TEXT PRIMARY KEY,
    node_id TEXT NOT NULL,
    allocation_id TEXT,
    execution_phase TEXT NOT NULL,
    outcome TEXT NOT NULL,
    entrypoint TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projected_quarantines (
    quarantine_id TEXT PRIMARY KEY,
    node_id TEXT NOT NULL,
    quarantine_state TEXT NOT NULL,
    reason TEXT NOT NULL,
    quarantined_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def get_projection_db_path() -> Path:
    return settings.data_root / "projection.db"


def connect_projection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target = db_path or get_projection_db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_projection_db(db_path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    conn = connect_projection(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_projection_db(db_path: Optional[Path] = None) -> None:
    with get_projection_db(db_path) as conn:
        conn.executescript(PROJECTION_SCHEMA)


def load_events_from_streams(stream_paths: list[Path]) -> list[dict[str, Any]]:
    """Read and merge events from all streams, sorted deterministically."""
    events: list[dict[str, Any]] = []
    for path in stream_paths:
        if not path.is_file():
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        doc = json.loads(line)
                        if doc.get("schema") == "ucc.event":
                            events.append(doc)
                    except Exception:
                        pass
        except Exception:
            pass

    events.sort(key=lambda e: (
        e.get("occurred_at", ""),
        e.get("producer", {}).get("module_id", ""),
        e.get("producer_sequence", 0),
        e.get("event_id", ""),
    ))
    return events


def apply_event_to_projection(conn: sqlite3.Connection, event: dict[str, Any]) -> None:
    event_id = event["event_id"]
    event_type = event["event_type"]
    occurred_at = event.get("occurred_at", now_iso())
    producer = event.get("producer", {})
    producer_module = producer.get("module_id", "unknown")
    actor_id = event.get("actor", {}).get("id", "act_unknown")
    subject = event.get("subject", {})
    subject_id = subject.get("id", "subj_unknown")
    producer_seq = event.get("producer_sequence", 0)
    payload = event.get("payload", {})
    payload_json = json.dumps(payload, sort_keys=True)

    conn.execute(
        """
        INSERT OR REPLACE INTO projected_events
        (event_id, event_type, occurred_at, producer_module, actor_id, subject_id, producer_sequence, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (event_id, event_type, occurred_at, producer_module, actor_id, subject_id, producer_seq, payload_json)
    )

    if "node" in event_type or subject.get("kind") == "node":
        node_id = subject_id
        name = payload.get("node_name", subject_id)
        if event_type == "node_quarantined":
            conn.execute(
                """
                INSERT INTO projected_nodes (node_id, display_name, readiness, quarantine_state, health, updated_at)
                VALUES (?, ?, 'quarantined', 'quarantined', 'degraded', ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    readiness='quarantined',
                    quarantine_state='quarantined',
                    health='degraded',
                    updated_at=excluded.updated_at
                """,
                (node_id, name, occurred_at)
            )
            q_id = f"rpt_{event_id[4:]}" if event_id.startswith("evt_") else event_id
            conn.execute(
                """
                INSERT OR REPLACE INTO projected_quarantines
                (quarantine_id, node_id, quarantine_state, reason, quarantined_at, updated_at)
                VALUES (?, ?, 'quarantined', ?, ?, ?)
                """,
                (q_id, node_id, payload.get("reason", "Quarantined"), occurred_at, occurred_at)
            )
        elif event_type in {"allocation_reserved", "node.reset_completed"}:
            conn.execute(
                """
                INSERT INTO projected_nodes (node_id, display_name, readiness, allocation_phase, updated_at)
                VALUES (?, ?, 'ready', 'reserved', ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    allocation_phase='reserved',
                    updated_at=excluded.updated_at
                """,
                (node_id, name, occurred_at)
            )
        elif event_type == "allocation_released":
            conn.execute(
                """
                INSERT INTO projected_nodes (node_id, display_name, readiness, allocation_phase, updated_at)
                VALUES (?, ?, 'ready', 'unallocated', ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    readiness='ready',
                    allocation_phase='unallocated',
                    updated_at=excluded.updated_at
                """,
                (node_id, name, occurred_at)
            )

    elif "artifact" in event_type or subject.get("kind") == "artifact":
        art_id = subject_id
        name = payload.get("name", art_id)
        status = payload.get("status", "draft")
        rev_id = payload.get("revision_id")
        content_hash = payload.get("content_hash")
        conn.execute(
            """
            INSERT INTO projected_artifacts (artifact_id, name, status, latest_revision_id, latest_hash, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(artifact_id) DO UPDATE SET
                status=excluded.status,
                latest_revision_id=COALESCE(excluded.latest_revision_id, projected_artifacts.latest_revision_id),
                latest_hash=COALESCE(excluded.latest_hash, projected_artifacts.latest_hash),
                updated_at=excluded.updated_at
            """,
            (art_id, name, status, rev_id, content_hash, occurred_at)
        )

    elif "execution" in event_type:
        exec_id = payload.get("execution_id", subject_id)
        node_id = payload.get("node_id", "node_unknown")
        alloc_id = payload.get("allocation_id")
        phase = payload.get("execution_phase", "completed")
        outcome = payload.get("outcome", "succeeded")
        entrypoint = payload.get("entrypoint", "run.sh")
        conn.execute(
            """
            INSERT INTO projected_executions
            (execution_id, node_id, allocation_id, execution_phase, outcome, entrypoint, started_at, completed_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(execution_id) DO UPDATE SET
                execution_phase=excluded.execution_phase,
                outcome=excluded.outcome,
                completed_at=COALESCE(excluded.completed_at, projected_executions.completed_at),
                updated_at=excluded.updated_at
            """,
            (exec_id, node_id, alloc_id, phase, outcome, entrypoint, occurred_at, occurred_at, occurred_at)
        )


def build_projection(stream_paths: list[Path], db_path: Optional[Path] = None) -> int:
    init_projection_db(db_path)
    events = load_events_from_streams(stream_paths)
    with get_projection_db(db_path) as conn:
        for event in events:
            apply_event_to_projection(conn, event)
    return len(events)


def rebuild_projection(stream_paths: list[Path], db_path: Optional[Path] = None) -> int:
    target = db_path or get_projection_db_path()
    if target.exists():
        target.unlink()
    return build_projection(stream_paths, target)
