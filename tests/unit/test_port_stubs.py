"""G3: ArtifactPort/FactoryPort stubs are Protocol-conformant, consumed in
app.state, and every method honestly refuses DEPENDENCY_UNAVAILABLE (no
real adapter is wired in until Stage 2 / G5)."""
from backend.ports.artifact_port_stub import ArtifactPortStub, build_artifact_port
from backend.ports.factory_port_stub import FactoryPortStub, build_factory_port
from ucc_contracts.ports import (
    ArtifactPort, CollectHandbackRequest, EligibilityRequest, ExecutionRequestEnvelope,
    FactoryPort, PortResult, RefusalCode, ReserveNodeRequest,
)

ARTIFACT_METHODS_DICT = {
    "get_revision": {"revision_id": "rev_x"},
    "resolve_publication": {"publication_id": "pub_x"},
    "create_script_revision": {"artifact_id": "art_x", "content": "echo ok"},
    "approve_revision": {"revision_id": "rev_x"},
    "publish_revision": {"revision_id": "rev_x", "channel": "execution"},
    "withdraw_publication": {"publication_id": "pub_x"},
}
FACTORY_METHODS_DICT = {
    "list_eligible_nodes": {},
    "release_node": {"allocation_id": "nalloc_x"},
    "get_execution": {"execution_id": "exec_x"},
    "cancel_execution": {"execution_id": "exec_x"},
    "reset_node": {"name": "w-01"},
    "quarantine_node": {"name": "w-01"},
    "get_node_health": {"name": "w-01"},
}


def test_artifact_stub_satisfies_protocol():
    assert isinstance(build_artifact_port(), ArtifactPort)


def test_factory_stub_satisfies_protocol():
    assert isinstance(build_factory_port(), FactoryPort)


def test_artifact_stub_validates_then_refuses_dependency_unavailable():
    stub = ArtifactPortStub()
    for name, valid_request in ARTIFACT_METHODS_DICT.items():
        invalid = getattr(stub, name)({})
        assert invalid.refusal_code == RefusalCode.VALIDATION_ERROR
        assert invalid.retryable is False
        result = getattr(stub, name)(valid_request)
        assert isinstance(result, PortResult)
        assert result.ok is False
        assert result.disposition == "refused"
        assert result.refusal_code == RefusalCode.DEPENDENCY_UNAVAILABLE
        assert result.retryable is True


def test_artifact_stub_eligibility_refuses_honestly():
    stub = ArtifactPortStub()
    result = stub.verify_execution_eligibility(
        EligibilityRequest(revision_id="rev_x", content_hash="sha256:" + "a" * 64,
                           channel="execution", entrypoint="run.sh"))
    assert result.eligible is False
    assert result.refusal_code == RefusalCode.DEPENDENCY_UNAVAILABLE


def test_factory_stub_validates_then_refuses_dependency_unavailable():
    stub = FactoryPortStub()
    for name, valid_request in FACTORY_METHODS_DICT.items():
        if valid_request:
            invalid = getattr(stub, name)({})
            assert invalid.refusal_code == RefusalCode.VALIDATION_ERROR
            assert invalid.retryable is False
        result = getattr(stub, name)(valid_request)
        assert isinstance(result, PortResult)
        assert result.ok is False
        assert result.disposition == "refused"
        assert result.refusal_code == RefusalCode.DEPENDENCY_UNAVAILABLE
        assert result.retryable is True


def test_factory_stub_typed_dto_methods_refuse_honestly():
    stub = FactoryPortStub()
    assert stub.reserve_node(ReserveNodeRequest(
        assignment_id="asn_x", capability_requirements=[], freshness_limit_seconds=60,
        idempotency_key="k")).refusal_code == RefusalCode.DEPENDENCY_UNAVAILABLE
    assert stub.request_execution(
        ExecutionRequestEnvelope(document={}, idempotency_key="k")
    ).refusal_code == RefusalCode.DEPENDENCY_UNAVAILABLE
    assert stub.collect_handback(
        CollectHandbackRequest(execution_id="exec_x", idempotency_key="k")
    ).refusal_code == RefusalCode.DEPENDENCY_UNAVAILABLE


def test_stubs_are_consumed_in_app_state(app):
    assert isinstance(app.state.artifact_port, ArtifactPort)
    assert isinstance(app.state.factory_port, FactoryPort)
