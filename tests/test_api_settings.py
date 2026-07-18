# test_api_settings.py - tests for /settings GET, PUT, and reset routes

import pytest
from fastapi.testclient import TestClient

from ccgen.api.app import app
from ccgen.config.defaults import get_default_settings


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def isolated_settings_file(tmp_path, monkeypatch):
    """Redirect settings persistence to a scratch file so tests never touch real user config."""
    settings_path = str(tmp_path / "settings.json")
    monkeypatch.setattr("ccgen.utils.settings.get_settings_file", lambda: settings_path)


class TestGetSettings:
    def test_status_ok(self, client):
        assert client.get("/settings").status_code == 200

    def test_returns_defaults_shape(self, client):
        assert client.get("/settings").json() == get_default_settings()


class TestPutSettings:
    def test_persists_value(self, client):
        resp = client.put("/settings", json={"key": "model.name", "value": "small"})
        assert resp.status_code == 200
        assert resp.json()["model"]["name"] == "small"

    def test_reflected_in_subsequent_get(self, client):
        client.put("/settings", json={"key": "ui.theme", "value": "dark"})
        assert client.get("/settings").json()["ui"]["theme"] == "dark"

    def test_missing_parent_keys_are_created(self, client):
        resp = client.put("/settings", json={"key": "custom_section.flag", "value": True})
        assert resp.json()["custom_section"]["flag"] is True

    def test_other_defaults_untouched(self, client):
        client.put("/settings", json={"key": "model.name", "value": "small"})
        data = client.get("/settings").json()
        assert data["transcription"] == get_default_settings()["transcription"]


class TestResetSettings:
    def test_restores_defaults(self, client):
        client.put("/settings", json={"key": "model.name", "value": "large-v3"})
        resp = client.post("/settings/reset")
        assert resp.status_code == 200
        assert resp.json() == get_default_settings()

    def test_reset_reflected_in_get(self, client):
        client.put("/settings", json={"key": "ui.theme", "value": "dark"})
        client.post("/settings/reset")
        assert client.get("/settings").json() == get_default_settings()
