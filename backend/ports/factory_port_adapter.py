"""Real in-process FactoryPort adapter (Stage 2 / S2-2, S2-3, roadmap §2)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from ucc_contracts.ports import (
    CollectHandbackRequest,
    ExecutionRequestEnvelope,
    FactoryPort,
    PortResult,
    RefusalCode,
    ReserveNodeRequest,
)


class InProcessFactoryPortAdapter:
    """Consumes the real VMFactoryFactoryPort implementation."""

    def __init__(self, state_dir: Optional[Path] = None):
        self._delegate: Optional[FactoryPort] = None
        self._init_error: Optional[str] = None
        target_state = state_dir or Path(".ucc-dev/vm-factory")
        try:
            from library.engine import NodeLifecycleEngine
            from library.factory_port import build_factory_port as vm_build
            engine = NodeLifecycleEngine(target_state)
            self._delegate = vm_build(engine)
        except ImportError:
            repo_root = Path(__file__).resolve().parents[2]
            vf_path = repo_root.parent / "stage2-VM-Factory"
            if vf_path.exists() and str(vf_path) not in sys.path:
                sys.path.insert(0, str(vf_path))
                try:
                    from library.engine import NodeLifecycleEngine
                    from library.factory_port import build_factory_port as vm_build
                    engine = NodeLifecycleEngine(target_state)
                    self._delegate = vm_build(engine)
                except Exception as exc:
                    self._init_error = str(exc)
            else:
                self._init_error = "VM-Factory package not importable"

    def list_eligible_nodes(self, request: dict) -> PortResult:
        if self._delegate:
            return self._delegate.list_eligible_nodes(request)
        return PortResult(
            ok=False,
            disposition="refused",
            refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
            message=f"VM-Factory backend is unavailable: {self._init_error}",
            retryable=True,
        )

    def reserve_node(self, request: ReserveNodeRequest) -> PortResult:
        if self._delegate:
            return self._delegate.reserve_node(request)
        return PortResult(
            ok=False,
            disposition="refused",
            refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
            message=f"VM-Factory backend is unavailable: {self._init_error}",
            retryable=True,
        )

    def release_node(self, request: dict) -> PortResult:
        if self._delegate:
            return self._delegate.release_node(request)
        return PortResult(
            ok=False,
            disposition="refused",
            refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
            message=f"VM-Factory backend is unavailable: {self._init_error}",
            retryable=True,
        )

    def request_execution(self, request: ExecutionRequestEnvelope) -> PortResult:
        if self._delegate:
            return self._delegate.request_execution(request)
        return PortResult(
            ok=False,
            disposition="refused",
            refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
            message=f"VM-Factory backend is unavailable: {self._init_error}",
            retryable=True,
        )

    def get_execution(self, request: dict) -> PortResult:
        if self._delegate:
            return self._delegate.get_execution(request)
        return PortResult(
            ok=False,
            disposition="refused",
            refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
            message=f"VM-Factory backend is unavailable: {self._init_error}",
            retryable=True,
        )

    def collect_handback(self, request: CollectHandbackRequest) -> PortResult:
        if self._delegate:
            return self._delegate.collect_handback(request)
        return PortResult(
            ok=False,
            disposition="refused",
            refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
            message=f"VM-Factory backend is unavailable: {self._init_error}",
            retryable=True,
        )

    def cancel_execution(self, request: dict) -> PortResult:
        if self._delegate:
            return self._delegate.cancel_execution(request)
        return PortResult(
            ok=False,
            disposition="refused",
            refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
            message=f"VM-Factory backend is unavailable: {self._init_error}",
            retryable=True,
        )

    def reset_node(self, request: dict) -> PortResult:
        if self._delegate:
            return self._delegate.reset_node(request)
        return PortResult(
            ok=False,
            disposition="refused",
            refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
            message=f"VM-Factory backend is unavailable: {self._init_error}",
            retryable=True,
        )

    def quarantine_node(self, request: dict) -> PortResult:
        if self._delegate:
            return self._delegate.quarantine_node(request)
        return PortResult(
            ok=False,
            disposition="refused",
            refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
            message=f"VM-Factory backend is unavailable: {self._init_error}",
            retryable=True,
        )

    def get_node_health(self, request: dict) -> PortResult:
        if self._delegate:
            return self._delegate.get_node_health(request)
        return PortResult(
            ok=False,
            disposition="refused",
            refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
            message=f"VM-Factory backend is unavailable: {self._init_error}",
            retryable=True,
        )


def build_factory_port(state_dir: Optional[Path] = None) -> FactoryPort:
    return InProcessFactoryPortAdapter(state_dir=state_dir)
