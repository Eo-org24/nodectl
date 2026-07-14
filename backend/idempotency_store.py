"""Per-owner idempotency/result store (M-b, D2).

Canonical evidence (backed up), not a disposable projection — a table
(`idempotency_records`, migration 003) in the existing `nodepanel.db`
nodectl already opens via `db.py`/`init_db()`, rather than a second SQLite
file. Only definite-success results are stored: a failed factory action is
safe and cheap to re-attempt, so it is not idempotency-tracked. This also
means an `unknown` disposition is never stored — nothing here ever becomes
a replay candidate until it has a definite, successful outcome.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Optional

from ucc_contracts.idempotency import StoredIdempotencyRecord


def request_fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class IdempotencyStore:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get(self, idempotency_key: str) -> Optional[StoredIdempotencyRecord]:
        row = self._conn.execute(
            "SELECT request_fingerprint, result_json FROM idempotency_records WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if row is None:
            return None
        return StoredIdempotencyRecord(
            idempotency_key=idempotency_key,
            request_fingerprint=row["request_fingerprint"],
            result=json.loads(row["result_json"]),
        )

    def put(self, *, idempotency_key: str, fingerprint: str, operation_type: str,
            disposition: str, result: dict, created_at: str) -> None:
        """Only ever called for a definite, non-`unknown` disposition — see
        module docstring. INSERT, not UPSERT: a caller reaching `put()` has
        already confirmed via `evaluate_idempotency()` that no conflicting
        record exists for this key."""
        self._conn.execute(
            "INSERT INTO idempotency_records "
            "(idempotency_key, request_fingerprint, operation_type, disposition, result_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (idempotency_key, fingerprint, operation_type, disposition,
             json.dumps(result, ensure_ascii=False, separators=(",", ":")), created_at),
        )
        self._conn.commit()
