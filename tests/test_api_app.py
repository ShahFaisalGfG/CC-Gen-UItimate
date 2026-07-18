# test_api_app.py - tests for the FastAPI app factory (health check, docs disabled)

import pytest
from fastapi.testclient import TestClient

from ccgen.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealth:
    def test_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestDocsDisabled:
    def test_docs_not_found(self, client):
        assert client.get("/docs").status_code == 404

    def test_redoc_not_found(self, client):
        assert client.get("/redoc").status_code == 404

    def test_openapi_json_not_found(self, client):
        assert client.get("/openapi.json").status_code == 404

    def test_app_config_disables_docs(self):
        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None
