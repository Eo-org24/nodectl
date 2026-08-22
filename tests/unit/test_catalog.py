"""Unit tests for S2-7: Command Catalog."""
from backend.catalog import CommandCatalog
from ucc_contracts import validate_document


def test_command_catalog_definitions_validate_against_schema():
    catalog = CommandCatalog()
    commands = catalog.list_commands()
    assert len(commands) >= 7
    for cmd in commands:
        validate_document("command-definition", cmd)


def test_command_catalog_lookup():
    catalog = CommandCatalog()
    reset_cmd = catalog.get_command("node.reset")
    assert reset_cmd is not None
    assert reset_cmd["implementation_kind"] == "ucc_builtin"
    assert reset_cmd["entrypoint"] == "builtin/node_reset.py"

    art_cmd = catalog.get_command("artifact.execute")
    assert art_cmd is not None
    assert art_cmd["implementation_kind"] == "published_artifact_revision"

    factory_cmds = catalog.list_by_kind("vm_factory_operation")
    assert len(factory_cmds) >= 3
