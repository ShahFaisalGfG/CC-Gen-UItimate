# transcription_ctrl.py — main transcription controller

import os

from PySide6.QtCore import Property, QObject, Qt, QThreadPool, QUrl, Signal, Slot

_MEDIA_EXTS = frozenset({
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".ts", ".m2ts",
    ".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma",
    ".srt", ".vtt",
})

from ccgen.config.defaults import (
    ComputeDefaults,
    ModelDefaults,
    OutputDefaults,
    TranslationDefaults,
    TransliterationDefaults,
)
from ccgen.core.pipeline import PipelineConfig, PipelineResult
from ccgen.models.file_model import MediaFileModel
from ccgen.services.worker import TranscriptionWorker


class TranscriptionController(QObject):
    """Manages the file queue, worker lifecycle, and all transcription settings."""

    busyChanged       = Signal(bool)
    segmentAdded      = Signal(int, float, float, str)
    progressChanged   = Signal(int, int)
    statusChanged     = Signal(str)
    operationFinished = Signal(bool, str, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_model = MediaFileModel()
        self._worker: TranscriptionWorker | None = None
        self._busy = False

        self._model_name  = ModelDefaults.DEFAULT_MODEL
        self._device      = ComputeDefaults.DEFAULT_DEVICE
        self._language: str | None = None
        self._translate   = TranslationDefaults.TRANSLATE_ENABLED
        self._target_lang = TranslationDefaults.DEFAULT_TARGET_LANG
        self._emit_srt    = OutputDefaults.FORMAT_SRT
        self._emit_vtt    = OutputDefaults.FORMAT_VTT
        self._transliterate  = TransliterationDefaults.ENABLED
        self._translit_src   = TransliterationDefaults.DEFAULT_SOURCE
        self._translit_tgt   = TransliterationDefaults.DEFAULT_TARGET
        self._translit_input = TransliterationDefaults.INPUT_SOURCE

    # ── Properties ───────────────────────────────────────────────────────────

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        """True while a worker is running."""
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

    # ── Processing slots ─────────────────────────────────────────────────────

    @Slot(str)
    def startProcessing(self, input_path: str) -> None:
        """Build config from current settings, create worker, and start it."""
        try:
            if self._busy or not input_path:
                return
            config = self._build_config(input_path)
            self._worker = TranscriptionWorker(config)
            self._connect_worker(self._worker)
            self._set_busy(True)
            QThreadPool.globalInstance().start(self._worker)
        except Exception as e:
            self.statusChanged.emit(f"Error: {e}")

    @Slot()
    def cancelProcessing(self) -> None:
        """Request cancellation of the current worker."""
        try:
            if self._worker is not None:
                self._worker.cancel()
        except Exception:
            pass

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _build_config(self, input_path: str) -> PipelineConfig:
        """Construct a PipelineConfig from the current controller state."""
        output_dir = os.path.dirname(input_path)
        return PipelineConfig(
            input_path=input_path,
            output_dir=output_dir,
            model_name=self._model_name,
            device=self._device,
            language=self._language,
            translate=self._translate,
            source_lang="auto",
            target_lang=self._target_lang,
            emit_srt=self._emit_srt,
            emit_vtt=self._emit_vtt,
            transliterate=self._transliterate,
            translit_source=self._translit_src,
            translit_target=self._translit_tgt,
            translit_input=self._translit_input,
        )

    def _connect_worker(self, worker: TranscriptionWorker) -> None:
        """Wire worker signals to controller slots using queued connections."""
        worker.signals.status.connect(self.statusChanged, Qt.ConnectionType.QueuedConnection)
        worker.signals.segment.connect(self.segmentAdded, Qt.ConnectionType.QueuedConnection)
        worker.signals.progress.connect(self.progressChanged, Qt.ConnectionType.QueuedConnection)
        worker.signals.finished.connect(self._on_finished, Qt.ConnectionType.QueuedConnection)

    def _set_busy(self, value: bool) -> None:
        """Update busy state and emit busyChanged."""
        if self._busy != value:
            self._busy = value
            self.busyChanged.emit(self._busy)

    @Slot(object)
    def _on_finished(self, result: object) -> None:
        """Handle worker completion: emit typed fields so QML can read them safely."""
        try:
            self._set_busy(False)
            if isinstance(result, PipelineResult):
                self.operationFinished.emit(result.success, result.error, result.output_files)
            else:
                self.operationFinished.emit(False, "Unknown error", [])
            self._worker = None
        except Exception:
            pass
