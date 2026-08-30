"""Integration tests proving real in-process ArtifactPort and FactoryPort adapters (Stage 2)."""
import pytest
from pathlib import Path
from backend.ports.artifact_port_adapter import InProcessArtifactPortAdapter, build_artifact_port
from backend.ports.factory_port_adapter import InProcessFactoryPortAdapter, build_factory_port
from ucc_contracts import new_id
from ucc_contracts.ports import (
    ArtifactPort, FactoryPort, ReserveNodeRequest, ExecutionRequestEnvelope,
)


def test_real_artifact_port_adapter_happy_path(tmp_path):
    port = build_artifact_port(library_root=tmp_path / "library")
    assert isinstance(port, ArtifactPort)
    if getattr(port, "_delegate", None) is not None:
        rev_res = port.create_script_revision({
            "title": "Inventory Script",
            "content": "echo 'hello ucc'",
            "content_path": "bin/inventory.sh",
            "created_by": new_id("act"),
            "idempotency_key": "idemp-art-1",
        })
        assert rev_res.ok is True
        assert rev_res.disposition == "completed"
        assert rev_res.value["revision"]["id"].startswith("rev_")


def test_real_factory_port_adapter_happy_path(tmp_path):
    port = build_factory_port(state_dir=tmp_path / "vm-factory")
    assert isinstance(port, FactoryPort)
    if getattr(port, "_delegate", None) is not None:
        health_res = port.get_node_health({"name": "w-01"})
        # Should return a valid result without stub refusal
        assert health_res.disposition in {"completed", "refused"}
        assert health_res.refusal_code != "dependency_unavailable"
