# test_transcription_queue.py - queue runner tests for ccgen.controllers.transcription_ctrl
#
# The embedded API is replaced by a fake client that records requests and lets each test
# play back job events, so the queue logic runs without a server, sockets, or models.

from typing import Any

import pytest
from PySide6.QtCore import QCoreApplication

from ccgen.controllers.transcription_ctrl import TranscriptionController
from ccgen.models.file_model import MediaFileModel


class _FakeSocket:
    """Stands in for QWebSocket: only the bits the controller touches."""

    class _Signal:
        def connect(self, *_):
            pass

        def disconnect(self, *_):
            pass

    errorOccurred = _Signal()

    def close(self):
        pass

    def deleteLater(self):
        pass


class _FakeApi:
    """Records calls and hands job ids out in order."""

    def __init__(self) -> None:
        self.posts: list[tuple[str, Any]] = []
        self.streams: dict[str, Any] = {}
        self._next_job = 0

    def get(self, path, handler=None):
        pass

    def post(self, path, body=None, handler=None):
        self.posts.append((path, body))
        if path == "/jobs" and handler is not None:
            self._next_job += 1
            handler({"job_id": f"job{self._next_job}"}, "")

    def open_stream(self, path, on_message):
        self.streams[path] = on_message
        return _FakeSocket()

    def send(self, job_id: str, event: dict) -> None:
        self.streams[f"/jobs/{job_id}/stream"](event)


@pytest.fixture
def controller(tmp_path):
    if QCoreApplication.instance() is None:
        QCoreApplication([])
    ctrl = TranscriptionController(base_url="http://127.0.0.1:1")
    ctrl._api = _FakeApi()  # type: ignore[assignment]
    return ctrl


@pytest.fixture
def three_files(tmp_path):
    paths = []
    for name in ("a.mp4", "b.mp3", "c.srt"):
        path = tmp_path / name
        path.write_bytes(b"data")
        paths.append(str(path))
    return paths


def _status(ctrl, row):
    return ctrl.fileModel.data(ctrl.fileModel.index(row), MediaFileModel.StatusRole)


def _finish(ctrl, job_id, success=True, error="", outputs=None):
    ctrl._api.send(job_id, {"event": "finished", "success": success, "error": error, "output_files": outputs or []})


class TestQueueRunner:
    def test_processes_every_file_in_order(self, controller, three_files):
        controller.addFiles(three_files)
        controller.startQueue()

        started = [body["input_path"] for path, body in controller._api.posts if path == "/jobs"]
        assert started == [three_files[0]]
        _finish(controller, "job1", outputs=["a.srt"])
        _finish(controller, "job2", outputs=["b.srt"])
        _finish(controller, "job3", outputs=["c_es.srt"])

        started = [body["input_path"] for path, body in controller._api.posts if path == "/jobs"]
        assert started == three_files
        assert [_status(controller, r) for r in range(3)] == ["done", "done", "done"]
        assert controller.busy is False
        assert controller.summary == "3 of 3 files done."
        assert ("/jobs/release-models", None) in controller._api.posts

    def test_failed_file_does_not_stop_the_run(self, controller, three_files):
        controller.addFiles(three_files)
        controller.startQueue()
        _finish(controller, "job1", success=False, error="ffmpeg missing")
        _finish(controller, "job2")
        _finish(controller, "job3")

        assert [_status(controller, r) for r in range(3)] == ["error", "done", "done"]
        message = controller.fileModel.data(controller.fileModel.index(0), MediaFileModel.MessageRole)
        assert message == "ffmpeg missing"
        assert "1 failed" in controller.summary

    def test_cancel_stops_run_and_start_resumes_remaining(self, controller, three_files):
        controller.addFiles(three_files)
        controller.startQueue()
        _finish(controller, "job1")
        controller.cancelQueue()
        assert ("/jobs/job2/cancel", None) in controller._api.posts
        _finish(controller, "job2", success=False, error="Cancelled by user.")

        assert controller.busy is False
        assert controller.summary == "Cancelled. 1 of 3 files done."
        assert [_status(controller, r) for r in range(3)] == ["done", "cancelled", "pending"]

        controller.startQueue()
        started = [body["input_path"] for path, body in controller._api.posts if path == "/jobs"]
        assert started[-1] == three_files[1]

    def test_all_done_queue_runs_again_from_the_start(self, controller, three_files):
        controller.addFiles(three_files[:1])
        controller.startQueue()
        _finish(controller, "job1")
        controller.startQueue()
        assert controller.busy is True
        assert _status(controller, 0) == "processing"

    def test_file_removed_mid_run_is_skipped(self, controller, three_files):
        controller.addFiles(three_files)
        controller.startQueue()
        controller.fileModel.removeAt(1)
        _finish(controller, "job1")

        started = [body["input_path"] for path, body in controller._api.posts if path == "/jobs"]
        assert started == [three_files[0], three_files[2]]

    def test_start_refused_without_output_format(self, controller, three_files):
        notices = []
        controller.notice.connect(notices.append)
        controller.addFiles(three_files)
        controller.setFormat("srt", False)

        controller.startQueue()

        assert controller.busy is False
        assert notices == ["Select at least one output format before starting."]

    def test_progress_updates_stage_and_row(self, controller, three_files):
        controller.addFiles(three_files[:1])
        controller.startQueue()
        controller._api.send("job1", {"event": "status", "message": "Transcribing..."})
        controller._api.send("job1", {"event": "progress", "done": 250, "total": 1000})

        assert controller.stage == "Transcribing..."
        assert controller.stageProgress == pytest.approx(0.25)
        progress = controller.fileModel.data(controller.fileModel.index(0), MediaFileModel.ProgressRole)
        assert progress == pytest.approx(0.25)

    def test_job_payload_uses_output_folder_and_language(self, controller, three_files, tmp_path):
        controller.addFiles(three_files[:1])
        controller.setOutputDir(str(tmp_path / "subs"))
        controller.setLanguage("ur")
        controller.startQueue()

        body = next(body for path, body in controller._api.posts if path == "/jobs")
        assert body["output_dir"] == str(tmp_path / "subs")
        assert (body["language"], body["source_lang"]) == ("ur", "ur")


class TestAddFiles:
    def test_unsupported_files_are_skipped_with_notice(self, controller, tmp_path):
        notices = []
        controller.notice.connect(notices.append)
        (tmp_path / "doc.pdf").write_bytes(b"x")
        (tmp_path / "v.mp4").write_bytes(b"x")

        controller.addFiles([str(tmp_path / "doc.pdf"), str(tmp_path / "v.mp4")])

        assert controller.fileModel.getPaths() == [str(tmp_path / "v.mp4")]
        assert notices == ["Skipped 1 unsupported file."]

    def test_file_urls_are_accepted(self, controller, tmp_path):
        (tmp_path / "v.mp4").write_bytes(b"x")
        controller.addFiles([(tmp_path / "v.mp4").as_uri()])
        assert controller.fileModel.count == 1
