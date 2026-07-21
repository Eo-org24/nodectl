"""ArtifactPort stub. See backend/ports/__init__.py for why every method
refuses today. Structurally identical to soloctl's own ArtifactPort adapter
(third_party/ucc-contracts/ucc_contracts/ports) — nodectl never imports
soloctl's domain code directly, only this Protocol."""
from __future__ import annotations

from ucc_contracts.ports import ArtifactPort, EligibilityRequest, EligibilityResult, PortResult, RefusalCode

_NOT_WIRED = (
    "No ArtifactPort adapter is wired into nodectl yet (Stage 2 / G5 work); "
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


class ArtifactPortStub:
    """`isinstance(ArtifactPortStub(), ArtifactPort)` holds via the
    Protocol's structural check (see tests/unit/test_port_stubs.py)."""

    def get_revision(self, request: dict) -> PortResult:
        return _require_keys(request, "revision_id") or _dependency_unavailable()

    def resolve_publication(self, request: dict) -> PortResult:
        return _require_keys(request, "publication_id") or _dependency_unavailable()

    def verify_execution_eligibility(self, request: EligibilityRequest) -> EligibilityResult:
        return EligibilityResult(eligible=False, refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE)

    def create_script_revision(self, request: dict) -> PortResult:
        return _require_keys(request, "artifact_id", "content") or _dependency_unavailable()

    def approve_revision(self, request: dict) -> PortResult:
        return _require_keys(request, "revision_id") or _dependency_unavailable()

    def publish_revision(self, request: dict) -> PortResult:
        return _require_keys(request, "revision_id", "channel") or _dependency_unavailable()

    def withdraw_publication(self, request: dict) -> PortResult:
        return _require_keys(request, "publication_id") or _dependency_unavailable()


def build_artifact_port() -> ArtifactPort:
    return ArtifactPortStub()
