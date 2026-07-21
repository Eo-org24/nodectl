"""FactoryPort stub. See backend/ports/__init__.py for why every method
refuses today. Structurally identical to VM-Factory's own FactoryPort
adapter (third_party/ucc-contracts/ucc_contracts/ports) — nodectl never
imports VM-Factory's domain code directly, only this Protocol.

Deliberately does not call anything in backend/ssh_client.py or
backend/services/factory.py: those are the fenced standalone-only infra
paths (tests/unit/test_infra_fence.py), and wiring them in here would be
exactly the bypass that fence exists to prevent.
"""
from __future__ import annotations

from ucc_contracts.ports import (
    CollectHandbackRequest, ExecutionRequestEnvelope, FactoryPort, PortResult, RefusalCode, ReserveNodeRequest,
)

_NOT_WIRED = (
    "No FactoryPort adapter is wired into nodectl yet (Stage 2 / G5 work); "
    "this stub exists so the port seam is real and consumable before the "
    "real in-process adapter lands."
)


def _dependency_unavailable() -> PortResult:
    return PortResult(ok=False, disposition="refused",
                      refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
                      message=_NOT_WIRED, retryable=True)


def _validation_refusal(message: str) -> PortResult:
    return PortResult(ok=False, disposition="refused",
                      refusal_code=RefusalCode.VALIDATION_ERROR,
                      message=message, retryable=False)


def _require_keys(request: dict, *keys: str) -> PortResult | None:
    missing = [key for key in keys if key not in request]
    if missing:
        return _validation_refusal(f"missing required field(s): {', '.join(missing)}")
    return None


class FactoryPortStub:
    """`isinstance(FactoryPortStub(), FactoryPort)` holds via the Protocol's
    structural check (see tests/unit/test_port_stubs.py)."""

    def list_eligible_nodes(self, request: dict) -> PortResult:
        return _dependency_unavailable()

    def reserve_node(self, request: ReserveNodeRequest) -> PortResult:
        return _dependency_unavailable()

    def release_node(self, request: dict) -> PortResult:
        return _require_keys(request, "allocation_id") or _dependency_unavailable()

    def request_execution(self, request: ExecutionRequestEnvelope) -> PortResult:
        return _dependency_unavailable()

    def get_execution(self, request: dict) -> PortResult:
        return _require_keys(request, "execution_id") or _dependency_unavailable()

    def collect_handback(self, request: CollectHandbackRequest) -> PortResult:
        return _dependency_unavailable()

    def cancel_execution(self, request: dict) -> PortResult:
        return _require_keys(request, "execution_id") or _dependency_unavailable()

    def reset_node(self, request: dict) -> PortResult:
        return _require_keys(request, "name") or _dependency_unavailable()

    def quarantine_node(self, request: dict) -> PortResult:
        return _require_keys(request, "name") or _dependency_unavailable()

    def get_node_health(self, request: dict) -> PortResult:
        return _require_keys(request, "name") or _dependency_unavailable()


def build_factory_port() -> FactoryPort:
    return FactoryPortStub()
