# test_api_settings.py - tests for /settings GET, PUT, and reset routes

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

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
    # Resetting defaults re-applies logging prefs; keep that from opening a real log file.
    monkeypatch.setattr("ccgen.api.services.settings_service.configure_from_settings", lambda *args: None)


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


class TestPatchSettings:
    def test_updates_several_keys_in_one_save(self, client):
        resp = client.patch("/settings", json={"values": {"model.name": "small", "output.vtt": True}})
        assert resp.status_code == 200
        data = client.get("/settings").json()
        assert data["model"]["name"] == "small"
        assert data["output"]["vtt"] is True

    def test_logging_change_reconfigures_logging(self, client):
        with patch("ccgen.api.services.settings_service.configure_from_settings") as configure:
            client.patch("/settings", json={"values": {"logging.log_level": "all"}})
        assert configure.call_args.args[0]["logging"]["log_level"] == "all"

    def test_concurrent_updates_are_not_lost(self, client):
        keys = [f"custom.k{i}" for i in range(12)]
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(lambda k: client.put("/settings", json={"key": k, "value": 1}), keys))
        assert set(client.get("/settings").json()["custom"]) == {k.split(".")[1] for k in keys}
