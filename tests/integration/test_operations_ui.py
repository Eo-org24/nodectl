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
    assert "Projected Nodes" in resp.text
    assert "Command Catalog" in resp.text
