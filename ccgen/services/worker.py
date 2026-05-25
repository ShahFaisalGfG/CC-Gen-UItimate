# worker.py — background transcription worker (PySide6)

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from ccgen.core import Segment
from ccgen.core.pipeline import Pipeline, PipelineConfig, PipelineResult


class WorkerSignals(QObject):
    """Signals emitted by TranscriptionWorker; must be created on the main thread."""

    status   = Signal(str)              # progress messages ("Loading model...", etc.)
    segment  = Signal(int, float, float, str)  # (id, start, end, text) per transcribed segment
    progress = Signal(int, int)         # (segments_done, total_estimated) — per segment
    finished = Signal(object)           # PipelineResult dataclass
    error    = Signal(str)              # fatal error string


class TranscriptionWorker(QRunnable):
    """Runs the full pipeline in a background thread, emitting live signals per segment."""

    def __init__(self, config: PipelineConfig) -> None:
        super().__init__()
        self.signals = WorkerSignals()
        self._config = config
        self._pipeline = Pipeline(config)
        self._cancelled = False
        self._segments_done = 0

    @Slot()
    def run(self) -> None:
        """Execute pipeline.prepare() then pipeline.run(); emit signals throughout."""
        try:
            self._pipeline.prepare(self.signals.status.emit)
            if self._cancelled:
                self._emit_cancelled()
                return
            result = self._pipeline.run(
                progress_cb=self.signals.status.emit,
                segment_cb=self._on_segment,
            )
            self.signals.progress.emit(self._segments_done, self._segments_done)
            if not result.success:
                self.signals.error.emit(result.error)
            self.signals.finished.emit(result)
        except Exception as e:
            err = str(e)
            self.signals.error.emit(err)
            self.signals.finished.emit(
                PipelineResult(success=False, input_path=self._config.input_path, error=err)
            )

    @Slot()
    def cancel(self) -> None:
        """Request cancellation — pipeline will finish its current segment."""
        self._cancelled = True

    def _on_segment(self, seg: Segment) -> None:
        """Forward a completed segment to the UI via queued signals."""
        try:
            self._segments_done += 1
            self.signals.segment.emit(seg["id"], seg["start"], seg["end"], seg["text"])
            self.signals.progress.emit(self._segments_done, 0)
        except Exception:
            pass

    def _emit_cancelled(self) -> None:
        """Emit a cancelled result when the worker is stopped before processing."""
        result = PipelineResult(
            success=False,
            input_path=self._config.input_path,
            error="Cancelled by user.",
        )
        self.signals.error.emit(result.error)
        self.signals.finished.emit(result)
