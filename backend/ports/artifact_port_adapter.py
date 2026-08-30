"""Real in-process ArtifactPort adapter (Stage 2 / S2-1, roadmap §2)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from ucc_contracts.ports import (
    ArtifactPort,
    EligibilityRequest,
    EligibilityResult,
    PortResult,
    RefusalCode,
)


class InProcessArtifactPortAdapter:
    """Consumes the real SoloctlArtifactPort implementation."""

    def __init__(
        self,
        library_root: Optional[Path] = None,
        canonical_root: Optional[Path] = None,
    ):
        self._delegate: Optional[ArtifactPort] = None
        self._init_error: Optional[str] = None
        try:
            from soloctl.artifact_port import build_artifact_port as soloctl_build
            self._delegate = soloctl_build(library_root=library_root, canonical_root=canonical_root)
        except ImportError:
            repo_root = Path(__file__).resolve().parents[2]
            ac_path = repo_root.parent / "stage2-Artifact-compiler"
            if ac_path.exists() and str(ac_path) not in sys.path:
                sys.path.insert(0, str(ac_path))
                try:
                    from soloctl.artifact_port import build_artifact_port as soloctl_build
                    self._delegate = soloctl_build(library_root=library_root, canonical_root=canonical_root)
                except Exception as exc:
                    self._init_error = str(exc)
            else:
                self._init_error = "soloctl package not importable"

    def get_revision(self, request: dict) -> PortResult:
        if self._delegate:
            return self._delegate.get_revision(request)
        return PortResult(
            ok=False,
            disposition="refused",
            refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
            message=f"Artifact Compiler backend is unavailable: {self._init_error}",
            retryable=True,
        )

    def resolve_publication(self, request: dict) -> PortResult:
        if self._delegate:
            return self._delegate.resolve_publication(request)
        return PortResult(
            ok=False,
            disposition="refused",
            refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
            message=f"Artifact Compiler backend is unavailable: {self._init_error}",
            retryable=True,
        )

    def verify_execution_eligibility(self, request: EligibilityRequest) -> EligibilityResult:
        if self._delegate:
            return self._delegate.verify_execution_eligibility(request)
        return EligibilityResult(eligible=False, refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE)

    def create_script_revision(self, request: dict) -> PortResult:
        if self._delegate:
            return self._delegate.create_script_revision(request)
        return PortResult(
            ok=False,
            disposition="refused",
            refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
            message=f"Artifact Compiler backend is unavailable: {self._init_error}",
            retryable=True,
        )

    def approve_revision(self, request: dict) -> PortResult:
        if self._delegate:
            return self._delegate.approve_revision(request)
        return PortResult(
            ok=False,
            disposition="refused",
            refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
            message=f"Artifact Compiler backend is unavailable: {self._init_error}",
            retryable=True,
        )

    def publish_revision(self, request: dict) -> PortResult:
        if self._delegate:
            return self._delegate.publish_revision(request)
        return PortResult(
            ok=False,
            disposition="refused",
            refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
            message=f"Artifact Compiler backend is unavailable: {self._init_error}",
            retryable=True,
        )

    def withdraw_publication(self, request: dict) -> PortResult:
        if self._delegate:
            return self._delegate.withdraw_publication(request)
        return PortResult(
            ok=False,
            disposition="refused",
            refusal_code=RefusalCode.DEPENDENCY_UNAVAILABLE,
            message=f"Artifact Compiler backend is unavailable: {self._init_error}",
            retryable=True,
        )


def build_artifact_port(
    library_root: Optional[Path] = None,
    canonical_root: Optional[Path] = None,
) -> ArtifactPort:
    return InProcessArtifactPortAdapter(library_root=library_root, canonical_root=canonical_root)
