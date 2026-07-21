"""Per-owner idempotency/result store (M-b, D2).

Canonical evidence (backed up), not a disposable projection — a table
(`idempotency_records`, migration 003) in the existing `nodepanel.db`
nodectl already opens via `db.py`/`init_db()`, rather than a second SQLite
file. An `unknown` row is committed before dispatch, replaced on success,
removed on definite failure, and retained after ambiguity so a retry cannot
silently execute the operation again. There is deliberately no auto-expiry.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from typing import Optional

from ucc_contracts.idempotency import StoredIdempotencyRecord


@dataclass(frozen=True)
class IdempotencyRecord(StoredIdempotencyRecord):
    disposition: str


def request_fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class IdempotencyStore:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get(self, idempotency_key: str) -> Optional[IdempotencyRecord]:
        row = self._conn.execute(
            "SELECT request_fingerprint, disposition, result_json "
            "FROM idempotency_records WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if row is None:
            return None
        return IdempotencyRecord(
            idempotency_key=idempotency_key,
            request_fingerprint=row["request_fingerprint"],
            disposition=row["disposition"],
            result=json.loads(row["result_json"]),
        )

    def put_in_flight(self, *, idempotency_key: str, fingerprint: str,
                      operation_type: str, created_at: str) -> None:
        self._conn.execute(
            "INSERT INTO idempotency_records "
            "(idempotency_key, request_fingerprint, operation_type, disposition, result_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (idempotency_key, fingerprint, operation_type, "unknown", "{}", created_at),
        )
        self._conn.commit()

    def complete(self, *, idempotency_key: str, result: dict) -> None:
        cursor = self._conn.execute(
            "UPDATE idempotency_records SET disposition = ?, result_json = ? "
            "WHERE idempotency_key = ?",
            ("completed", json.dumps(result, ensure_ascii=False, separators=(",", ":")),
             idempotency_key),
        )
        if cursor.rowcount != 1:
            raise RuntimeError(f"missing in-flight idempotency record for {idempotency_key!r}")
        self._conn.commit()

    def delete(self, idempotency_key: str) -> None:
        self._conn.execute(
            "DELETE FROM idempotency_records WHERE idempotency_key = ?",
            (idempotency_key,),
        )
        self._conn.commit()
