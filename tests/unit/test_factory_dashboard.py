from __future__ import annotations

from backend.routers.api import parse_virsh_list
from backend.ssh_client import normalize_manifest_record


def test_parse_virsh_list_handles_separator_and_multiword_state():
    output = """
 Id   Name              State
----------------------------------
 7    worker-02         running
 -    worker-03         shut off
"""
    assert parse_virsh_list(output) == [
        {"id": "7", "name": "worker-02", "state": "running"},
        {"id": "-", "name": "worker-03", "state": "shut off"},
    ]


def test_normalize_manifest_record_uses_metadata_and_spec_fallbacks():
    manifest = {
        "metadata": {"name": "worker-03"},
        "spec": {"template": "worker", "state": "ready"},
    }

    record = normalize_manifest_record("nodes/worker-03/node.yaml", manifest)

    assert record["name"] == "worker-03"
    assert record["type"] == "worker"
    assert record["state"] == "ready"
    assert record["path"] == "nodes/worker-03/node.yaml"
