# transcription_ctrl.py — main transcription controller (HTTP/WebSocket client of the API)

import json
import os
from typing import Any, Optional

from PySide6.QtCore import Property, QByteArray, QObject, QUrl, Signal, Slot
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWebSockets import QWebSocket

from ccgen.config.defaults import (
    ComputeDefaults,
    ModelDefaults,
    OutputDefaults,
    TranslationDefaults,
    TransliterationDefaults,
)
from ccgen.models.file_model import MediaFileModel

_MEDIA_EXTS = frozenset({
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".ts", ".m2ts",
    ".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma",
    ".srt", ".vtt", ".lrc", ".ass", ".ssa", ".sbv",
})


class TranscriptionController(QObject):
    """Manages the file queue and job settings, and drives jobs via the embedded API."""

    busyChanged       = Signal(bool)
    segmentAdded      = Signal(int, float, float, str)
    # 64-bit: this also carries raw byte progress during pipeline.prepare()'s model
    # download phase - a plain 32-bit Qt `int` overflows past ~2.147 GB (e.g. the
    # large-v3 Whisper model, ~3.1 GB), silently dropping the event.
    progressChanged   = Signal('qlonglong', 'qlonglong')  # type: ignore[arg-type]
    statusChanged     = Signal(str)
    operationFinished = Signal(bool, str, list)
    defaultsLoaded    = Signal()

    def __init__(self, base_url: str, parent=None):
        super().__init__(parent)
        self._base_url = base_url
        self._net = QNetworkAccessManager(self)
        self._socket: Optional[QWebSocket] = None
        self._job_id: Optional[str] = None
        self._file_model = MediaFileModel()
        self._busy = False

        self._model_name  = ModelDefaults.DEFAULT_MODEL
        self._device      = ComputeDefaults.DEFAULT_DEVICE
        self._language: Optional[str] = None
        self._translate   = TranslationDefaults.TRANSLATE_ENABLED
        self._target_lang = TranslationDefaults.DEFAULT_TARGET_LANG
        self._emit_srt    = OutputDefaults.FORMAT_SRT
        self._emit_vtt    = OutputDefaults.FORMAT_VTT
        self._emit_lrc    = OutputDefaults.FORMAT_LRC
        self._emit_ass    = OutputDefaults.FORMAT_ASS
        self._emit_sbv    = OutputDefaults.FORMAT_SBV
        self._transliterate   = TransliterationDefaults.ENABLED
        self._translit_src    = TransliterationDefaults.DEFAULT_SOURCE
        self._translit_tgt    = TransliterationDefaults.DEFAULT_TARGET
        self._translit_input  = TransliterationDefaults.INPUT_SOURCE
        self._translit_engine = TransliterationDefaults.DEFAULT_ENGINE
        self._fetch_defaults()

    # ── Properties ───────────────────────────────────────────────────────────

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        """True while a job is running."""
        return self._busy

    @Property(QObject, constant=True)
    def fileModel(self) -> MediaFileModel:
        """The shared media file queue model."""
        return self._file_model

    @Property(str)
    def modelName(self) -> str:
        return self._model_name

    @Property(str)
    def language(self) -> str:
        return self._language or ""

    @Property(bool)
    def translateEnabled(self) -> bool:
        return self._translate

    @Property(str)
    def targetLang(self) -> str:
        return self._target_lang

    @Property(bool)
    def emitSrt(self) -> bool:
        return self._emit_srt

    @Property(bool)
    def emitVtt(self) -> bool:
        return self._emit_vtt

    @Property(bool)
    def emitLrc(self) -> bool:
        return self._emit_lrc

    @Property(bool)
    def emitAss(self) -> bool:
        return self._emit_ass

    @Property(bool)
    def emitSbv(self) -> bool:
        return self._emit_sbv

    @Property(bool)
    def transliterateEnabled(self) -> bool:
        return self._transliterate

    @Property(str)
    def translitSource(self) -> str:
        return self._translit_src

    @Property(str)
    def translitTarget(self) -> str:
        return self._translit_tgt

    @Property(str)
    def translitInput(self) -> str:
        return self._translit_input

    @Property(str)
    def translitEngine(self) -> str:
        return self._translit_engine

    # ── File queue slots ─────────────────────────────────────────────────────

    @Slot(list)
    def addFiles(self, urls: list) -> None:
        """Accept QML URL or string paths and forward to the file model."""
        try:
            paths = [
                u.toLocalFile() if hasattr(u, "toLocalFile") else str(u)
                for u in urls
            ]
            self._file_model.addFiles(paths)
        except Exception:
            pass

    @Slot(str)
    def addFolder(self, folder_url: str) -> None:
        """Scan a folder for supported media/subtitle files and add them."""
        try:
            folder = QUrl(folder_url).toLocalFile() if folder_url.startswith("file") else folder_url
            if not os.path.isdir(folder):
                return
            paths = sorted(
                os.path.join(folder, f)
                for f in os.listdir(folder)
                if os.path.splitext(f)[1].lower() in _MEDIA_EXTS
            )
            self._file_model.addFiles(paths)
        except Exception:
            pass

    @Slot(int)
    def removeFile(self, row: int) -> None:
        """Remove the file at the given row from the queue."""
        self._file_model.removeAt(row)

    @Slot()
    def removeSelected(self) -> None:
        """Remove all selected files from the queue."""
        self._file_model.removeSelected()

    # ── Settings slots ───────────────────────────────────────────────────────

    @Slot(str)
    def setModelName(self, name: str) -> None:
        self._model_name = name

    @Slot(str)
    def setLanguage(self, code: str) -> None:
        self._language = code if code else None

    @Slot(bool)
    def setTranslate(self, enabled: bool) -> None:
        self._translate = enabled

    @Slot(str)
    def setTargetLang(self, lang: str) -> None:
        self._target_lang = lang

    @Slot(bool)
    def setEmitSrt(self, value: bool) -> None:
        self._emit_srt = value

    @Slot(bool)
    def setEmitVtt(self, value: bool) -> None:
        self._emit_vtt = value

    @Slot(bool)
    def setEmitLrc(self, value: bool) -> None:
        self._emit_lrc = value

    @Slot(bool)
    def setEmitAss(self, value: bool) -> None:
        self._emit_ass = value

    @Slot(bool)
    def setEmitSbv(self, value: bool) -> None:
        self._emit_sbv = value

    @Slot(bool)
    def setTransliterate(self, enabled: bool) -> None:
        self._transliterate = enabled

    @Slot(str)
    def setTranslitSource(self, scheme: str) -> None:
        self._translit_src = scheme

    @Slot(str)
    def setTranslitTarget(self, scheme: str) -> None:
        self._translit_tgt = scheme

    @Slot(str)
    def setTranslitInput(self, source: str) -> None:
        self._translit_input = source

    @Slot(str)
    def setTranslitEngine(self, engine: str) -> None:
        self._translit_engine = engine

    # ── Processing slots ─────────────────────────────────────────────────────

    @Slot(str)
    def startProcessing(self, input_path: str) -> None:
        """POST a new job to the embedded API and start streaming its progress."""
        try:
            if self._busy or not input_path:
                return
            payload = self._build_job_payload(input_path)
            body = QByteArray(json.dumps(payload).encode("utf-8"))
            request = QNetworkRequest(QUrl(f"{self._base_url}/jobs"))
            request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
            reply = self._net.post(request, body)
            reply.finished.connect(lambda: self._on_job_started(reply))
            self._set_busy(True)
        except Exception as e:
            self.statusChanged.emit(f"Error: {e}")

    @Slot()
    def cancelProcessing(self) -> None:
        """Request cancellation of the current job via the embedded API."""
        try:
            if self._job_id is None:
                return
            request = QNetworkRequest(QUrl(f"{self._base_url}/jobs/{self._job_id}/cancel"))
            reply = self._net.post(request, QByteArray())
            reply.finished.connect(reply.deleteLater)
        except Exception:
            pass

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _fetch_defaults(self) -> None:
        """Asynchronously seed job settings from the embedded API's persisted defaults."""
        request = QNetworkRequest(QUrl(f"{self._base_url}/settings"))
        reply = self._net.get(request)
        reply.finished.connect(lambda: self._on_defaults_fetched(reply))

    def _on_defaults_fetched(self, reply: QNetworkReply) -> None:
        """Apply persisted defaults fetched at startup, then notify QML once."""
        try:
            reply.deleteLater()
            if reply.error() == QNetworkReply.NetworkError.NoError:
                settings: dict[str, Any] = json.loads(bytes(reply.readAll().data()).decode("utf-8"))
                self._apply_defaults(settings)
        except Exception:
            pass
        finally:
            self.defaultsLoaded.emit()

    def _apply_defaults(self, settings: dict[str, Any]) -> None:
        """Seed session state from a fetched settings dictionary."""
        model = settings.get("model", {})
        translation = settings.get("translation", {})
        output = settings.get("output", {})
        translit = settings.get("transliteration", {})

        self._model_name  = model.get("name", self._model_name)
        self._translate   = translation.get("enabled", self._translate)
        self._target_lang = translation.get("target_lang", self._target_lang)
        self._emit_srt    = output.get("srt", self._emit_srt)
        self._emit_vtt    = output.get("vtt", self._emit_vtt)
        self._emit_lrc    = output.get("lrc", self._emit_lrc)
        self._emit_ass    = output.get("ass", self._emit_ass)
        self._emit_sbv    = output.get("sbv", self._emit_sbv)
        self._transliterate   = translit.get("enabled", self._transliterate)
        self._translit_src    = translit.get("source", self._translit_src)
        self._translit_tgt    = translit.get("target", self._translit_tgt)
        self._translit_input  = translit.get("input_source", self._translit_input)
        self._translit_engine = translit.get("engine", self._translit_engine)

    def _build_job_payload(self, input_path: str) -> dict[str, Any]:
        """Build the JSON job config from current controller state."""
        return {
            "input_path": input_path,
            "output_dir": os.path.dirname(input_path),
            "model_name": self._model_name,
            "device": self._device,
            "language": self._language,
            "translate": self._translate,
            "source_lang": "auto",
            "target_lang": self._target_lang,
            "emit_srt": self._emit_srt,
            "emit_vtt": self._emit_vtt,
            "emit_lrc": self._emit_lrc,
            "emit_ass": self._emit_ass,
            "emit_sbv": self._emit_sbv,
            "transliterate": self._transliterate,
            "translit_source": self._translit_src,
            "translit_target": self._translit_tgt,
            "translit_input": self._translit_input,
            "translit_engine": self._translit_engine,
        }

    def _on_job_started(self, reply: QNetworkReply) -> None:
        """Handle the POST /jobs response: parse the job id and open its event stream."""
        try:
            reply.deleteLater()
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self._set_busy(False)
                self.operationFinished.emit(False, reply.errorString(), [])
                return
            data = json.loads(bytes(reply.readAll().data()).decode("utf-8"))
            job_id: str = data["job_id"]
            self._job_id = job_id
            self._open_stream(job_id)
        except Exception as e:
            self._set_busy(False)
            self.operationFinished.emit(False, str(e), [])

    def _open_stream(self, job_id: str) -> None:
        """Open a WebSocket to the job's event stream and wire event handling."""
        ws_url = self._base_url.replace("http://", "ws://").replace("https://", "wss://")
        self._socket = QWebSocket()
        self._socket.textMessageReceived.connect(self._on_stream_message)
        self._socket.open(QUrl(f"{ws_url}/jobs/{job_id}/stream"))

    def _on_stream_message(self, message: str) -> None:
        """Parse one JSON event from the job stream and re-emit the matching Qt signal."""
        try:
            event: dict[str, Any] = json.loads(message)
            kind = event.get("event")
            if kind == "segment":
                self.segmentAdded.emit(event["id"], event["start"], event["end"], event["text"])
            elif kind == "progress":
                self.progressChanged.emit(event["done"], event["total"])
            elif kind == "status":
                self.statusChanged.emit(event["message"])
            elif kind == "finished":
                self._set_busy(False)
                self.operationFinished.emit(
                    bool(event.get("success")),
                    event.get("error") or "",
                    event.get("output_files") or [],
                )
                self._close_stream()
        except Exception:
            pass

    def _close_stream(self) -> None:
        """Close and release the current job's WebSocket."""
        try:
            if self._socket is not None:
                self._socket.close()
                self._socket.deleteLater()
                self._socket = None
        except Exception:
            pass

    def _set_busy(self, value: bool) -> None:
        """Update busy state and emit busyChanged."""
        if self._busy != value:
            self._busy = value
            self.busyChanged.emit(self._busy)
