# transcription_ctrl.py - file queue, job options, and the queue runner (client of the embedded API)
#
# Every file in the queue runs as its own API job, one after another: start job, stream its
# events, record the result on the file's row, move to the next file. Cancelling stops the
# running job and leaves the remaining files pending, so Start resumes where the run stopped.

import os
from typing import Any, Optional

from PySide6.QtCore import Property, QObject, QThreadPool, Signal, Slot
from PySide6.QtWebSockets import QWebSocket

from ccgen.config.defaults import (
    ComputeDefaults,
    ModelDefaults,
    OutputDefaults,
    TranslationDefaults,
    TransliterationDefaults,
)
from ccgen.controllers.api_client import ApiClient
from ccgen.models.file_model import (
    STATUS_CANCELLED,
    STATUS_DONE,
    STATUS_ERROR,
    STATUS_PROCESSING,
    SUPPORTED_EXTS,
    MediaFileModel,
)
from ccgen.services.folder_scanner import FolderScanWorker
from ccgen.utils.helpers import plural, to_local_path

_FORMATS = ("srt", "vtt", "lrc", "ass", "sbv")


def _option_property(name: str, kind: type, notify: Signal) -> Property:
    """Build a notifying Qt property that reads one entry of the controller's options dict."""
    return Property(kind, lambda self: kind(self._options[name]), notify=notify)


class TranscriptionController(QObject):
    """Manages the file queue and job options, and runs the queue through the embedded API."""

    busyChanged       = Signal(bool)
    optionsChanged    = Signal()
    runStateChanged   = Signal()
    scanChanged       = Signal()
    segmentAdded      = Signal(int, float, float, str, str)  # (id, start, end, text, kind)
    fileStarted       = Signal(str, str)        # (path, file name)
    notice            = Signal(str)             # one-off message shown to the user

    def __init__(self, base_url: str, parent=None):
        super().__init__(parent)
        self._api = ApiClient(base_url, self)
        self._file_model = MediaFileModel(self)
        self._socket: Optional[QWebSocket] = None
        self._job_id: Optional[str] = None
        self._busy = False

        self._options: dict[str, Any] = {
            "model_name": ModelDefaults.DEFAULT_MODEL,
            "device": ComputeDefaults.DEFAULT_DEVICE,
            "compute_type": ComputeDefaults.DEFAULT_COMPUTE_TYPE,
            "language": "",
            "vad_filter": True,
            "translate": TranslationDefaults.TRANSLATE_ENABLED,
            "target_lang": TranslationDefaults.DEFAULT_TARGET_LANG,
            "emit_srt": OutputDefaults.FORMAT_SRT,
            "emit_vtt": OutputDefaults.FORMAT_VTT,
            "emit_lrc": OutputDefaults.FORMAT_LRC,
            "emit_ass": OutputDefaults.FORMAT_ASS,
            "emit_sbv": OutputDefaults.FORMAT_SBV,
            "max_line_length": OutputDefaults.MAX_LINE_LENGTH,
            "max_lines": OutputDefaults.MAX_LINES,
            "output_dir": OutputDefaults.DIRECTORY,
            "transliterate": TransliterationDefaults.ENABLED,
            "translit_source": TransliterationDefaults.DEFAULT_SOURCE,
            "translit_target": TransliterationDefaults.DEFAULT_TARGET,
            "translit_input": TransliterationDefaults.INPUT_SOURCE,
            "translit_engine": TransliterationDefaults.DEFAULT_ENGINE,
        }

        self._run_paths: list[str] = []
        self._run_index = -1
        self._run_ok = 0
        self._run_failed = 0
        self._cancel_requested = False
        self._current_path = ""
        self._stage = ""
        self._stage_progress = -1.0
        self._summary = ""
        self._last_outputs: list[str] = []

        self._scan: Optional[FolderScanWorker] = None
        self._scan_found = 0

        self._api.get("/settings", self._on_defaults_fetched)

    # ── Queue and status properties ──────────────────────────────────────────

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        """True while the queue is being processed."""
        return self._busy

    @Property(QObject, constant=True)
    def fileModel(self) -> MediaFileModel:
        """The shared media file queue model."""
        return self._file_model

    @Property(bool, notify=scanChanged)
    def scanning(self) -> bool:
        """True while a folder scan is adding files in the background."""
        return self._scan is not None

    @Property(int, notify=scanChanged)
    def scanFound(self) -> int:
        """Files found so far by the running folder scan."""
        return self._scan_found

    @Property(str, notify=runStateChanged)
    def currentFile(self) -> str:
        """Name of the file being processed, empty when idle."""
        return os.path.basename(self._current_path)

    @Property(int, notify=runStateChanged)
    def runPosition(self) -> int:
        """1-based position of the current file within this run."""
        return self._run_index + 1 if self._busy else 0

    @Property(int, notify=runStateChanged)
    def runTotal(self) -> int:
        """Number of files in the current run."""
        return len(self._run_paths)

    @Property(str, notify=runStateChanged)
    def stage(self) -> str:
        """What the current file is doing (loading model, transcribing, translating...)."""
        return self._stage

    @Property(float, notify=runStateChanged)
    def stageProgress(self) -> float:
        """Progress of the current stage from 0 to 1, or -1 when it can't be measured."""
        return self._stage_progress

    @Property(float, notify=runStateChanged)
    def overallProgress(self) -> float:
        """Progress of the whole run from 0 to 1."""
        if not self._run_paths:
            return 0.0
        done = max(0, self._run_index) + max(0.0, self._stage_progress)
        return min(1.0, done / len(self._run_paths))

    @Property(str, notify=runStateChanged)
    def summary(self) -> str:
        """One-line result of the last finished run."""
        return self._summary

    @Property(str, notify=runStateChanged)
    def lastOutputFolder(self) -> str:
        """Folder holding the most recently written subtitle file."""
        return os.path.dirname(self._last_outputs[-1]) if self._last_outputs else ""

    # ── Option properties (notify so QML bindings stay in sync) ─────────────

    modelName            = _option_property("model_name", str, optionsChanged)
    device               = _option_property("device", str, optionsChanged)
    language             = _option_property("language", str, optionsChanged)
    translateEnabled     = _option_property("translate", bool, optionsChanged)
    targetLang           = _option_property("target_lang", str, optionsChanged)
    emitSrt              = _option_property("emit_srt", bool, optionsChanged)
    emitVtt              = _option_property("emit_vtt", bool, optionsChanged)
    emitLrc              = _option_property("emit_lrc", bool, optionsChanged)
    emitAss              = _option_property("emit_ass", bool, optionsChanged)
    emitSbv              = _option_property("emit_sbv", bool, optionsChanged)
    outputDir            = _option_property("output_dir", str, optionsChanged)
    transliterateEnabled = _option_property("transliterate", bool, optionsChanged)
    translitSource       = _option_property("translit_source", str, optionsChanged)
    translitTarget       = _option_property("translit_target", str, optionsChanged)
    translitInput        = _option_property("translit_input", str, optionsChanged)
    translitEngine       = _option_property("translit_engine", str, optionsChanged)

    @Property(bool, notify=optionsChanged)
    def hasOutputFormat(self) -> bool:
        """True when at least one subtitle format is enabled."""
        return any(self._options[f"emit_{fmt}"] for fmt in _FORMATS)

    # ── Option setters ───────────────────────────────────────────────────────

    def _set(self, name: str, value: Any) -> None:
        """Store an option and notify QML when it changed."""
        if self._options.get(name) != value:
            self._options[name] = value
            self.optionsChanged.emit()

    @Slot(str)
    def setModelName(self, name: str) -> None:
        self._set("model_name", name)

    @Slot(str)
    def setLanguage(self, code: str) -> None:
        self._set("language", code or "")

    @Slot(bool)
    def setTranslate(self, enabled: bool) -> None:
        self._set("translate", enabled)

    @Slot(str)
    def setTargetLang(self, lang: str) -> None:
        self._set("target_lang", lang)

    @Slot(str, bool)
    def setFormat(self, fmt: str, enabled: bool) -> None:
        """Enable or disable one output format ("srt", "vtt", "lrc", "ass", "sbv")."""
        if fmt in _FORMATS:
            self._set(f"emit_{fmt}", enabled)

    @Slot(str)
    def setOutputDir(self, folder: str) -> None:
        """Set the output folder ("" writes next to each input file); accepts file:// URLs."""
        self._set("output_dir", to_local_path(folder) if folder else "")

    @Slot(bool)
    def setTransliterate(self, enabled: bool) -> None:
        self._set("transliterate", enabled)

    @Slot(str)
    def setTranslitSource(self, scheme: str) -> None:
        self._set("translit_source", scheme)

    @Slot(str)
    def setTranslitTarget(self, scheme: str) -> None:
        self._set("translit_target", scheme)

    @Slot(str)
    def setTranslitInput(self, source: str) -> None:
        self._set("translit_input", source)

    @Slot(str)
    def setTranslitEngine(self, engine: str) -> None:
        self._set("translit_engine", engine)

    @Slot()
    def reloadDefaults(self) -> None:
        """Re-seed job options from the saved preferences (after Preferences are saved)."""
        if not self._busy:
            self._api.get("/settings", self._on_defaults_fetched)

    # ── File queue slots ─────────────────────────────────────────────────────

    @Slot(list)
    def addFiles(self, urls: list) -> None:
        """Add dropped or picked files; folders among them are scanned in the background."""
        paths = [to_local_path(u) for u in urls]
        folders = [p for p in paths if p and os.path.isdir(p)]
        files = [p for p in paths if p and p not in folders and os.path.splitext(p)[1].lower() in SUPPORTED_EXTS]
        skipped = len(paths) - len(folders) - len(files)
        before = self._file_model.count
        self._file_model.addFiles(files)
        if folders:
            self._start_scan(folders)
        if skipped:
            self.notice.emit(f"Skipped {plural(skipped, 'unsupported file')}.")
        elif files and self._file_model.count == before:
            self.notice.emit("Those files are already in the queue.")

    @Slot(str)
    def addFolder(self, folder_url: str) -> None:
        """Scan a folder and its subfolders for supported files, in the background."""
        folder = to_local_path(folder_url)
        if folder and os.path.isdir(folder):
            self._start_scan([folder])

    @Slot()
    def cancelScan(self) -> None:
        """Stop the running folder scan; files already found stay in the queue."""
        if self._scan is not None:
            self._scan.cancel()

    @Slot()
    def clearQueue(self) -> None:
        """Stop any folder scan and remove every file that isn't being processed."""
        self.cancelScan()
        self._file_model.clearAll()

    # ── Processing slots ─────────────────────────────────────────────────────

    @Slot()
    def startQueue(self) -> None:
        """Process every unfinished file in the queue (or all files when all are done)."""
        if self._busy:
            return
        if not self.hasOutputFormat:
            self.notice.emit("Select at least one output format before starting.")
            return
        paths = self._file_model.runnable_paths()
        if not paths:
            self.notice.emit("Add media or subtitle files to the queue first.")
            return
        self._file_model.reset_for_run(paths)
        self._run_paths = paths
        self._run_index = -1
        self._run_ok = self._run_failed = 0
        self._cancel_requested = False
        self._summary = ""
        self._last_outputs = []
        self._set_busy(True)
        self._start_next()

    @Slot()
    def cancelQueue(self) -> None:
        """Stop the running file and leave the rest of the queue pending."""
        if not self._busy or self._cancel_requested:
            return
        self._cancel_requested = True
        self._set_stage("Cancelling...", -1.0)
        if self._job_id is not None:
            self._api.post(f"/jobs/{self._job_id}/cancel")

    # ── Queue runner ─────────────────────────────────────────────────────────

    def _start_next(self) -> None:
        """Start the next file still in the queue, or finish the run."""
        while True:
            self._run_index += 1
            if self._cancel_requested or self._run_index >= len(self._run_paths):
                self._finish_run()
                return
            path = self._run_paths[self._run_index]
            if self._file_model.contains(path):
                break
        self._current_path = path
        self._job_id = None
        self._file_model.set_run_state(path, status=STATUS_PROCESSING, progress=0.0)
        self._set_stage("Starting...", -1.0)
        self.fileStarted.emit(path, os.path.basename(path))
        self._api.post("/jobs", self._job_payload(path), self._on_job_started)

    def _job_payload(self, input_path: str) -> dict[str, Any]:
        """Build the JSON job config for one file from the current options."""
        opts = self._options
        return {
            "input_path": input_path,
            "output_dir": opts["output_dir"] or os.path.dirname(input_path),
            "model_name": opts["model_name"],
            "device": opts["device"],
            "compute_type": opts["compute_type"],
            "language": opts["language"] or None,
            "vad_filter": opts["vad_filter"],
            "translate": opts["translate"],
            "source_lang": opts["language"] or "auto",
            "target_lang": opts["target_lang"],
            **{f"emit_{fmt}": opts[f"emit_{fmt}"] for fmt in _FORMATS},
            "max_line_length": opts["max_line_length"],
            "max_lines": opts["max_lines"],
            "transliterate": opts["transliterate"],
            "translit_source": opts["translit_source"],
            "translit_target": opts["translit_target"],
            "translit_input": opts["translit_input"],
            "translit_engine": opts["translit_engine"],
        }

    def _on_job_started(self, data: Any, error: str) -> None:
        """Open the job's event stream, or record the failure and move on."""
        if error or not isinstance(data, dict) or "job_id" not in data:
            self._on_file_finished(False, error or "The job could not be started.", [])
            return
        self._job_id = str(data["job_id"])
        if self._cancel_requested:
            self._api.post(f"/jobs/{self._job_id}/cancel")
        self._socket = self._api.open_stream(f"/jobs/{self._job_id}/stream", self._on_stream_event)
        self._socket.errorOccurred.connect(self._on_stream_error)

    def _on_stream_event(self, event: dict[str, Any]) -> None:
        """Route one job event to the matching signal and row update."""
        kind = event.get("event")
        if kind == "segment":
            self.segmentAdded.emit(
                int(event["id"]), float(event["start"]), float(event["end"]),
                str(event["text"]), str(event.get("kind", "transcript")),
            )
        elif kind == "progress":
            done, total = int(event["done"]), int(event["total"])
            fraction = min(1.0, done / total) if total > 0 else -1.0
            self._set_stage(self._stage, fraction)
            if fraction >= 0:
                self._file_model.set_run_state(self._current_path, progress=fraction)
        elif kind == "status":
            self._set_stage(str(event.get("message", "")), -1.0)
        elif kind == "finished":
            self._close_stream()
            self._on_file_finished(
                bool(event.get("success")), str(event.get("error") or ""), list(event.get("output_files") or []),
            )

    def _on_stream_error(self, *_args) -> None:
        """Treat a dropped event stream as a failed file so the run never stalls."""
        if self._socket is None:
            return
        message = self._socket.errorString()
        self._close_stream()
        self._on_file_finished(False, f"Lost connection to the processing service: {message}", [])

    def _on_file_finished(self, success: bool, error: str, outputs: list[str]) -> None:
        """Record one file's result and continue with the next file."""
        path = self._current_path
        cancelled = not success and self._cancel_requested
        if success:
            self._run_ok += 1
            self._last_outputs.extend(outputs)
            status, message = STATUS_DONE, f"{plural(len(outputs), 'subtitle file')} written"
        elif cancelled:
            status, message = STATUS_CANCELLED, "Cancelled"
        else:
            self._run_failed += 1
            status, message = STATUS_ERROR, error or "Unknown error"
        self._file_model.set_run_state(
            path, status=status, progress=1.0 if success else 0.0, message=message, outputs=outputs,
        )
        self._job_id = None
        self._start_next()

    def _finish_run(self) -> None:
        """Wrap up the run: summary, idle state, and release cached models."""
        cancelled = self._cancel_requested
        summary = f"{self._run_ok} of {plural(len(self._run_paths), 'file')} done"
        if self._run_failed:
            summary += f", {self._run_failed} failed"
        self._summary = f"Cancelled. {summary}." if cancelled else f"{summary}."
        self._current_path = ""
        self._set_stage("", -1.0)
        self._set_busy(False)
        self._api.post("/jobs/release-models")
        self.notice.emit(self._summary)

    def _close_stream(self) -> None:
        """Close and release the current job's WebSocket."""
        socket, self._socket = self._socket, None
        if socket is not None:
            socket.errorOccurred.disconnect(self._on_stream_error)
            socket.close()
            socket.deleteLater()

    def _set_stage(self, stage: str, progress: float) -> None:
        """Update the stage label and progress, notifying QML."""
        self._stage = stage
        self._stage_progress = progress
        self.runStateChanged.emit()

    def _set_busy(self, value: bool) -> None:
        """Update busy state and emit busyChanged."""
        if self._busy != value:
            self._busy = value
            self.busyChanged.emit(value)
            self.runStateChanged.emit()

    # ── Folder scanning ──────────────────────────────────────────────────────

    def _start_scan(self, folders: list[str]) -> None:
        """Scan folders on the thread pool, replacing any scan already running."""
        self.cancelScan()
        worker = FolderScanWorker(folders, SUPPORTED_EXTS)
        worker.signals.batchFound.connect(self._on_scan_batch)
        worker.signals.progress.connect(self._on_scan_progress)
        worker.signals.error.connect(self.notice)
        worker.signals.finished.connect(lambda found, cancelled, w=worker: self._on_scan_finished(w, found, cancelled))
        self._scan = worker
        self._scan_found = 0
        self.scanChanged.emit()
        QThreadPool.globalInstance().start(worker)

    def _on_scan_batch(self, entries: list) -> None:
        """Insert one batch of scanned files."""
        self._file_model.addScanned(entries)

    def _on_scan_progress(self, found: int) -> None:
        """Track the running file count for the scanning indicator."""
        self._scan_found = found
        self.scanChanged.emit()

    def _on_scan_finished(self, worker: FolderScanWorker, found: int, cancelled: bool) -> None:
        """Clear scan state and tell the user what the scan found."""
        if self._scan is worker:
            self._scan = None
            self.scanChanged.emit()
        if cancelled:
            return
        self.notice.emit(f"Found {plural(found, 'supported file')}." if found else "No supported files in that folder.")

    def shutdown(self) -> None:
        """Stop background work before the app exits so the thread pool can drain quickly."""
        self.cancelScan()
        if self._job_id is not None:
            self._api.post(f"/jobs/{self._job_id}/cancel")

    # ── Defaults ─────────────────────────────────────────────────────────────

    def _on_defaults_fetched(self, settings: Any, error: str) -> None:
        """Seed job options from persisted preferences."""
        if not error and isinstance(settings, dict):
            self._apply_defaults(settings)

    def _apply_defaults(self, settings: dict[str, Any]) -> None:
        """Copy the saved defaults into the session options."""
        model = settings.get("model", {})
        transcription = settings.get("transcription", {})
        translation = settings.get("translation", {})
        output = settings.get("output", {})
        translit = settings.get("transliteration", {})
        opts = self._options
        opts["model_name"] = model.get("name", opts["model_name"])
        opts["device"] = model.get("device", opts["device"])
        opts["compute_type"] = model.get("compute_type", opts["compute_type"])
        opts["language"] = transcription.get("language") or ""
        opts["vad_filter"] = bool(transcription.get("vad_filter", opts["vad_filter"]))
        opts["translate"] = bool(translation.get("enabled", opts["translate"]))
        opts["target_lang"] = translation.get("target_lang", opts["target_lang"])
        for fmt in _FORMATS:
            opts[f"emit_{fmt}"] = bool(output.get(fmt, opts[f"emit_{fmt}"]))
        opts["max_line_length"] = int(output.get("max_line_length", opts["max_line_length"]))
        opts["max_lines"] = int(output.get("max_lines", opts["max_lines"]))
        opts["output_dir"] = output.get("directory") or ""
        opts["transliterate"] = bool(translit.get("enabled", opts["transliterate"]))
        opts["translit_source"] = translit.get("source", opts["translit_source"])
        opts["translit_target"] = translit.get("target", opts["translit_target"])
        opts["translit_input"] = translit.get("input_source", opts["translit_input"])
        opts["translit_engine"] = translit.get("engine", opts["translit_engine"])
        self.optionsChanged.emit()
