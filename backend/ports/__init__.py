"""nodectl's port adapters (Stage 2 / G5).

Reaches Artifact Compiler and VM-Factory through real in-process adapters
implementing ArtifactPort and FactoryPort contracts.
"""
from __future__ import annotations

from .artifact_port_adapter import InProcessArtifactPortAdapter, build_artifact_port
from .factory_port_adapter import InProcessFactoryPortAdapter, build_factory_port

__all__ = [
    "InProcessArtifactPortAdapter",
    "InProcessFactoryPortAdapter",
    "build_artifact_port",
    "build_factory_port",
]
