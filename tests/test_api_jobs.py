# test_api_jobs.py — integration tests for the FastAPI job/settings/options routes

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ccgen.api.app import app
from ccgen.core.pipeline import PipelineResult


@pytest.fixture
def client():
    """A fresh TestClient per test, so each test gets its own portal/event loop."""
    with TestClient(app) as c:
        yield c


def _fake_result(input_path: str) -> PipelineResult:
    """Build a successful PipelineResult for mocking Pipeline.run()."""
    return PipelineResult(
        success=True,
        input_path=input_path,
        output_files=[f"{input_path}.srt"],
        detected_language="en",
    )


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestJobFlow:
    def test_start_job_and_stream_events(self, client, tmp_path):
        fake = tmp_path / "video.mp4"
        fake.write_bytes(b"fake")

        with patch("ccgen.core.pipeline.Pipeline.prepare"):
            with patch("ccgen.core.pipeline.Pipeline.run", return_value=_fake_result(str(fake))):
                resp = client.post("/jobs", json={"input_path": str(fake)})
                assert resp.status_code == 200
                job_id = resp.json()["job_id"]

                events = []
                with client.websocket_connect(f"/jobs/{job_id}/stream") as ws:
                    while True:
                        event = ws.receive_json()
                        events.append(event)
                        if event["event"] == "finished":
                            break

        assert events[-1]["success"] is True
        assert events[-1]["output_files"] == [f"{fake}.srt"]

    def test_get_job_status_after_finish(self, client, tmp_path):
        fake = tmp_path / "video.mp4"
        fake.write_bytes(b"fake")

        with patch("ccgen.core.pipeline.Pipeline.prepare"):
            with patch("ccgen.core.pipeline.Pipeline.run", return_value=_fake_result(str(fake))):
                job_id = client.post("/jobs", json={"input_path": str(fake)}).json()["job_id"]
                with client.websocket_connect(f"/jobs/{job_id}/stream") as ws:
                    while ws.receive_json()["event"] != "finished":
                        pass

        status = client.get(f"/jobs/{job_id}").json()
        assert status["busy"] is False
        assert status["success"] is True

    def test_unknown_job_returns_404(self, client):
        assert client.get("/jobs/does-not-exist").status_code == 404

    def test_cancel_unknown_job_returns_404(self, client):
        assert client.post("/jobs/does-not-exist/cancel").status_code == 404


class TestSettingsAndOptions:
    def test_get_settings_returns_dict(self, client):
        resp = client.get("/settings")
        assert resp.status_code == 200
        assert "model" in resp.json()

    def test_put_setting_roundtrip(self, client):
        resp = client.put("/settings", json={"key": "ui.theme", "value": "dark"})
        assert resp.status_code == 200
        assert resp.json()["ui"]["theme"] == "dark"
        client.put("/settings", json={"key": "ui.theme", "value": "system"})

    def test_get_options_returns_expected_keys(self, client):
        data = client.get("/options").json()
        assert "translit_engines" in data
        assert {"label": "Rule-based (fast, offline)", "code": "rule"} in data["translit_engines"]
