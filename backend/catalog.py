"""Command Catalog over surviving typed routes (S2-7, UCC-Standards §17).

Defines and validates command definitions for:
- ucc_builtin: builtin node operations
- published_artifact_revision: approved artifact execution
- vm_factory_operation: VM-Factory port operations
"""
from __future__ import annotations

from typing import Any, Optional

from ucc_contracts import new_id, validate_document


CATALOG_DEFINITIONS: list[dict[str, Any]] = [
    {
        "schema": "ucc.command-definition",
        "schema_version": 1,
        "id": "op_01M0NW6TX9RXWAFGQ71WS63001",
        "created_at": "2026-08-22T12:00:00.000Z",
        "created_by": "act_01M0NW6TX9RXWAFGQ71WS63000",
        "record_version": 1,
        "name": "node.reset",
        "implementation_kind": "ucc_builtin",
        "entrypoint": "builtin/node_reset.py",
        "parameters_schema": {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        },
    },
    {
        "schema": "ucc.command-definition",
        "schema_version": 1,
        "id": "op_01M0NW6TX9RXWAFGQ71WS63002",
        "created_at": "2026-08-22T12:00:00.000Z",
        "created_by": "act_01M0NW6TX9RXWAFGQ71WS63000",
        "record_version": 1,
        "name": "node.quarantine",
        "implementation_kind": "ucc_builtin",
        "entrypoint": "builtin/node_quarantine.py",
        "parameters_schema": {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}, "reason": {"type": "string"}},
        },
    },
    {
        "schema": "ucc.command-definition",
        "schema_version": 1,
        "id": "op_01M0NW6TX9RXWAFGQ71WS63003",
        "created_at": "2026-08-22T12:00:00.000Z",
        "created_by": "act_01M0NW6TX9RXWAFGQ71WS63000",
        "record_version": 1,
        "name": "node.health",
        "implementation_kind": "ucc_builtin",
        "entrypoint": "builtin/node_health.py",
        "parameters_schema": {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        },
    },
    {
        "schema": "ucc.command-definition",
        "schema_version": 1,
        "id": "op_01M0NW6TX9RXWAFGQ71WS63004",
        "created_at": "2026-08-22T12:00:00.000Z",
        "created_by": "act_01M0NW6TX9RXWAFGQ71WS63000",
        "record_version": 1,
        "name": "artifact.execute",
        "implementation_kind": "published_artifact_revision",
        "entrypoint": "run.sh",
        "parameters_schema": {
            "type": "object",
            "required": ["revision_id"],
            "properties": {"revision_id": {"type": "string"}},
        },
    },
    {
        "schema": "ucc.command-definition",
        "schema_version": 1,
        "id": "op_01M0NW6TX9RXWAFGQ71WS63005",
        "created_at": "2026-08-22T12:00:00.000Z",
        "created_by": "act_01M0NW6TX9RXWAFGQ71WS63000",
        "record_version": 1,
        "name": "factory.reserve",
        "implementation_kind": "vm_factory_operation",
        "entrypoint": "reserve_node",
        "parameters_schema": {
            "type": "object",
            "required": ["assignment_id"],
            "properties": {"assignment_id": {"type": "string"}},
        },
    },
    {
        "schema": "ucc.command-definition",
        "schema_version": 1,
        "id": "op_01M0NW6TX9RXWAFGQ71WS63006",
        "created_at": "2026-08-22T12:00:00.000Z",
        "created_by": "act_01M0NW6TX9RXWAFGQ71WS63000",
        "record_version": 1,
        "name": "factory.execution",
        "implementation_kind": "vm_factory_operation",
        "entrypoint": "request_execution",
        "parameters_schema": {
            "type": "object",
            "required": ["allocation_id", "entrypoint"],
            "properties": {"allocation_id": {"type": "string"}, "entrypoint": {"type": "string"}},
        },
    },
    {
        "schema": "ucc.command-definition",
        "schema_version": 1,
        "id": "op_01M0NW6TX9RXWAFGQ71WS63007",
        "created_at": "2026-08-22T12:00:00.000Z",
        "created_by": "act_01M0NW6TX9RXWAFGQ71WS63000",
        "record_version": 1,
        "name": "factory.handback",
        "implementation_kind": "vm_factory_operation",
        "entrypoint": "collect_handback",
        "parameters_schema": {
            "type": "object",
            "required": ["execution_id"],
            "properties": {"execution_id": {"type": "string"}},
        },
    },
]


class CommandCatalog:
    def __init__(self, definitions: Optional[list[dict[str, Any]]] = None):
        self._definitions = definitions or CATALOG_DEFINITIONS
        for cmd in self._definitions:
            validate_document("command-definition", cmd)

    def list_commands(self) -> list[dict[str, Any]]:
        return list(self._definitions)

    def get_command(self, name: str) -> Optional[dict[str, Any]]:
        for cmd in self._definitions:
            if cmd["name"] == name:
                return cmd
        return None

    def list_by_kind(self, kind: str) -> list[dict[str, Any]]:
        return [cmd for cmd in self._definitions if cmd["implementation_kind"] == kind]
