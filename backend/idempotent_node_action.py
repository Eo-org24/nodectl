"""Idempotent wrapper around `run_factory_script`, called from the
`POST /api/nodes/{node_name}/action/{action}` route when an
`X-Idempotency-Key` header is present (M-b — closes G2's request/result/
problem + idempotency requirement for one real nodectl operation).

Additive: the route's non-idempotent path (no header) is unchanged. The
idempotent path commits `unknown` before dispatch. Success replaces that
row, definite failure removes it, and an ambiguous exception retains it so
the same request refuses `outcome_unknown` instead of dispatching twice.
"""
from __future__ import annotations

import sqlite3

from ucc_contracts import new_id, validate_document
from ucc_contracts.idempotency import (
    IdempotencyOutcome, evaluate_idempotency, idempotency_conflict_problem,
)

from .idempotency_store import IdempotencyStore, request_fingerprint
from .ssh_client import run_factory_script
from .ucc_events import deterministic_id, ucc_now_iso


class IdempotencyConflictError(Exception):
    def __init__(self, problem: dict) -> None:
        self.problem = problem
        super().__init__(problem["message"])


class OutcomeUnknownError(Exception):
    def __init__(self, problem: dict) -> None:
        self.problem = problem
        super().__init__(problem["message"])


def _outcome_unknown_problem(*, request_id: str, operation_id: str,
                             correlation_id: str) -> dict:
    problem = {
        "schema": "ucc.problem", "schema_version": 1,
        "kind": "outcome_unknown", "code": "outcome_unknown",
        "message": "a prior dispatch has an unknown outcome; reconcile it before retrying",
        "retryable": False,
        "request_id": request_id, "operation_id": operation_id,
        "correlation_id": correlation_id,
    }
    validate_document("problem", problem)
    return problem


async def run_node_action_idempotent(
    conn: sqlite3.Connection, *, node_name: str, action: str,
    idempotency_key: str, actor_username: str,
) -> dict:
    """Returns a dict with the same keys as run_factory_script's result
    (command/stdout/stderr/exit_code) plus an embedded validated `result`
    envelope and a `_replayed` flag — the caller (route) must skip the
    ledger write + event emission when `_replayed` is True, since a replay
    did not actually re-run the action and logging it again would
    misrepresent history. Raises IdempotencyConflictError on conflict
    (caller maps this to a refusal); ValueError propagates unchanged for an
    unsupported action, exactly as the non-idempotent path already does."""
    store = IdempotencyStore(conn)
    payload = {"node_name": node_name, "action": action}
    fingerprint = request_fingerprint(payload)
    stored = store.get(idempotency_key)
    outcome = evaluate_idempotency(idempotency_key, fingerprint, stored)

    request_id = new_id("req")
    operation_id = new_id("op")
    correlation_id = new_id("corr")

    if outcome == IdempotencyOutcome.REPLAY and stored.disposition == "unknown":
        raise OutcomeUnknownError(_outcome_unknown_problem(
            request_id=request_id, operation_id=operation_id,
            correlation_id=correlation_id))

    if outcome == IdempotencyOutcome.REPLAY:
        return {**stored.result, "_replayed": True}

    if outcome == IdempotencyOutcome.CONFLICT:
        raise IdempotencyConflictError(idempotency_conflict_problem(
            request_id=request_id, operation_id=operation_id, correlation_id=correlation_id))

    request_doc = {
        "schema": "ucc.request", "schema_version": 1,
        "request_id": request_id, "operation_id": operation_id, "correlation_id": correlation_id,
        "causation_id": None, "idempotency_key": idempotency_key,
        "request_fingerprint": fingerprint, "requested_at": ucc_now_iso(),
        "requested_by": deterministic_id("act", f"actor:{actor_username}"),
        "operation_type": f"node.{action}", "payload": payload,
    }
    validate_document("request", request_doc)

    store.put_in_flight(
        idempotency_key=idempotency_key, fingerprint=fingerprint,
        operation_type=f"node.{action}", created_at=request_doc["requested_at"],
    )

    try:
        exec_result = await run_factory_script(node_name=node_name, action=action)
    except ValueError:
        store.delete(idempotency_key)
        raise

    disposition = "completed" if exec_result["exit_code"] == 0 else "failed"
    result_doc = {
        "schema": "ucc.result", "schema_version": 1,
        "result_id": new_id("res"), "request_id": request_id, "operation_id": operation_id,
        "correlation_id": correlation_id, "completed_at": ucc_now_iso(),
        "disposition": disposition,
        "resource": {"kind": "node", "id": deterministic_id("node", f"node:{node_name}")},
        "warnings": [],
    }
    validate_document("result", result_doc)
    value = {**exec_result, "result": result_doc}
    if disposition == "completed":
        store.complete(idempotency_key=idempotency_key, result=value)
    else:
        store.delete(idempotency_key)
    return {**value, "_replayed": False}
