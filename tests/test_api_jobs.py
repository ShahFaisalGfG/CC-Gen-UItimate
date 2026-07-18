# test_api_jobs.py - tests for job start/poll/cancel routes and the live event websocket

import threading
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from ccgen.api.app import app
from ccgen.core.pipeline import PipelineResult

_SEGMENT = {"id": 0, "start": 0.0, "end": 1.0, "text": "hi", "words": [], "language": "en"}


@pytest.fixture
def client():
    """A TestClient kept open for the whole test so job_manager's background task survives."""
    with TestClient(app) as c:
        yield c


def _job_payload(tmp_path):
    """Build a minimal JobConfig body pointing at a path the mocked pipeline never reads."""
    return {"input_path": str(tmp_path / "video.mp4")}


def _start_job(client, tmp_path):
    """Post a job and return its job_id, asserting the request succeeded."""
    resp = client.post("/jobs", json=_job_payload(tmp_path))
    assert resp.status_code == 200
    return resp.json()["job_id"]


def _default_run(status_cb, segment_cb, progress_num_cb):
    """Fast stand-in for Pipeline.run() used when a test does not care about callbacks."""
    return PipelineResult(success=True, input_path="in.mp4", output_files=[])


def _fake_pipeline_cls(prepare_side_effect=None, run_side_effect=None):
    """Build a fake Pipeline class whose instances invoke the callbacks job_manager passes in."""
    instance = MagicMock()
    instance.prepare.side_effect = prepare_side_effect or (lambda status_cb, progress_num_cb: None)
    instance.run.side_effect = run_side_effect or _default_run
    return MagicMock(return_value=instance), instance


def _collect_until_finished(ws, limit=10):
    """Read websocket JSON events until a 'finished' event arrives, or bail after limit reads."""
    events = []
    for _ in range(limit):
        event = ws.receive_json()
        events.append(event)
        if event.get("event") == "finished":
            break
    return events


class TestStartJob:
    def test_returns_job_id(self, client, tmp_path):
        pipeline_cls, _ = _fake_pipeline_cls()
        with patch("ccgen.api.services.job_manager.Pipeline", pipeline_cls):
            job_id = _start_job(client, tmp_path)
        assert isinstance(job_id, str) and job_id

    def test_missing_input_path_returns_422(self, client):
        resp = client.post("/jobs", json={})
        assert resp.status_code == 422


class TestGetJob:
    def test_unknown_id_returns_404(self, client):
        assert client.get("/jobs/does-not-exist").status_code == 404

    def test_busy_then_completed_shape(self, client, tmp_path):
        run_can_finish = threading.Event()

        def blocking_run(status_cb, segment_cb, progress_num_cb):
            segment_cb(_SEGMENT)
            progress_num_cb(1, 1)
            run_can_finish.wait(timeout=5)
            return PipelineResult(success=True, input_path="in.mp4", output_files=["out.srt"])

        pipeline_cls, _ = _fake_pipeline_cls(run_side_effect=blocking_run)
        with patch("ccgen.api.services.job_manager.Pipeline", pipeline_cls):
            job_id = _start_job(client, tmp_path)
            assert client.get(f"/jobs/{job_id}").json() == {"job_id": job_id, "busy": True}

            with client.websocket_connect(f"/jobs/{job_id}/stream") as ws:
                run_can_finish.set()
                events = _collect_until_finished(ws)

        assert events[-1]["event"] == "finished"
        assert client.get(f"/jobs/{job_id}").json() == {
            "job_id": job_id, "busy": False, "success": True,
            "error": "", "output_files": ["out.srt"],
        }


class TestStreamJob:
    def test_events_arrive_in_order_and_finish(self, client, tmp_path):
        def fake_run(status_cb, segment_cb, progress_num_cb):
            segment_cb(_SEGMENT)
            progress_num_cb(1, 1)
            return PipelineResult(success=True, input_path="in.mp4", output_files=["out.srt"])

        pipeline_cls, _ = _fake_pipeline_cls(run_side_effect=fake_run)
        with patch("ccgen.api.services.job_manager.Pipeline", pipeline_cls):
            job_id = _start_job(client, tmp_path)
            with client.websocket_connect(f"/jobs/{job_id}/stream") as ws:
                events = _collect_until_finished(ws)

        assert [e["event"] for e in events] == ["segment", "progress", "finished"]
        assert events[0]["text"] == "hi"
        assert events[1] == {"event": "progress", "done": 1, "total": 1}
        assert events[2] == {
            "event": "finished", "success": True, "error": "", "output_files": ["out.srt"],
        }


class TestCancelJob:
    def test_unknown_id_returns_404(self, client):
        assert client.post("/jobs/does-not-exist/cancel").status_code == 404

    def test_cancel_before_run_reports_cancelled(self, client, tmp_path):
        prepare_can_finish = threading.Event()

        def blocking_prepare(status_cb, progress_num_cb):
            prepare_can_finish.wait(timeout=5)

        def unexpected_run(*args, **kwargs):
            raise AssertionError("pipeline.run() must not run for a job cancelled before it")

        pipeline_cls, instance = _fake_pipeline_cls(
            prepare_side_effect=blocking_prepare, run_side_effect=unexpected_run,
        )
        with patch("ccgen.api.services.job_manager.Pipeline", pipeline_cls):
            job_id = _start_job(client, tmp_path)

            cancel_resp = client.post(f"/jobs/{job_id}/cancel")
            assert cancel_resp.status_code == 200
            assert cancel_resp.json() == {"cancelled": True}
            prepare_can_finish.set()

            with client.websocket_connect(f"/jobs/{job_id}/stream") as ws:
                finished = ws.receive_json()

        assert finished == {
            "event": "finished", "success": False,
            "error": "Cancelled by user.", "output_files": [],
        }
        instance.run.assert_not_called()
