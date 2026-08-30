"""Integration tests for the operator surface fixture operation view."""
import pytest
from fastapi.testclient import TestClient
from backend.auth import issue_session


@pytest.fixture
def client(app, app_settings):
    with TestClient(app) as test_client:
        resp = test_client.post("/login", data={"username": "admin", "password": "admin-pass"}, follow_redirects=True)
        assert resp.status_code == 200
        yield test_client


def test_operations_tab_renders_successfully(client):
    resp = client.get("/tab/operations")
    assert resp.status_code == 200
    assert "UCC Operations (Projection-Backed)" in resp.text
    assert "Correlated Operation" in resp.text
    assert "Correlated Event Timeline" in resp.text
    assert "Projected Nodes" in resp.text
    assert "Command Catalog" in resp.text

    # Operator finish line: assert actual correlated values
    assert "prj_" in resp.text
    assert "job_" in resp.text
    assert "asn_" in resp.text
    assert "op_" in resp.text
    assert "art_" in resp.text
    assert "rev_" in resp.text
    assert "pub_" in resp.text
    assert "node_" in resp.text or "w-01" in resp.text
    assert "sha256:" in resp.text
    assert "completed" in resp.text or "running" in resp.text
