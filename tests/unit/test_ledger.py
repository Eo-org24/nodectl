from __future__ import annotations

from backend.ledger import VALID_TOOL, Ledger, read_entries


def test_valid_tool_dual_accepts_legacy_nodepanel_during_transition():
    # D5: writer identifier is retired to "nodectl", but "nodepanel" stays
    # accepted so entries from before the rename still validate.
    assert "nodectl" in VALID_TOOL
    assert "nodepanel" in VALID_TOOL
    assert "soloctl" in VALID_TOOL


def test_ledger_writer_now_tags_entries_nodectl(tmp_path):
    ledger = Ledger(root=str(tmp_path), tool="nodectl")
    ledger.write(actor="human:test", action="node.action", target="node:vm-01", status="ok")
    ledger_file = next((tmp_path / "ledger").glob("*.jsonl"))
    entries = list(read_entries(ledger_file))
    assert entries[0]["tool"] == "nodectl"


def test_read_entries_tolerates_legacy_nodepanel_tool_tag(tmp_path):
    # Same ledger dir, two writers: one pre-rename ("nodepanel"), one
    # post-rename ("nodectl"). The tolerant reader must not choke on either.
    legacy = Ledger(root=str(tmp_path), tool="nodepanel")
    legacy.write(actor="human:test", action="git.deploy", target="node:vm-01", status="ok")
    current = Ledger(root=str(tmp_path), tool="nodectl")
    current.write(actor="human:test", action="git.deploy", target="node:vm-01", status="ok")

    ledger_file = next((tmp_path / "ledger").glob("*.jsonl"))
    tools = [entry["tool"] for entry in read_entries(ledger_file)]
    assert tools == ["nodepanel", "nodectl"]
