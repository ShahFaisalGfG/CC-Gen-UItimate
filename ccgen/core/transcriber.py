# transcriber.py — faster-whisper wrapper producing word-timestamped segments

import os
from typing import Callable, Iterator, Optional

from faster_whisper import WhisperModel

from ccgen.config.defaults import ComputeDefaults, ModelDefaults, TranscriptionDefaults
from ccgen.core import Segment, WordToken


class Transcriber:
    """Wraps faster-whisper; loads the model once and transcribes on demand."""

    def __init__(
        self,
        model_name: str = ModelDefaults.DEFAULT_MODEL,
        device: str = ComputeDefaults.DEFAULT_DEVICE,
        compute_type: str = ComputeDefaults.DEFAULT_COMPUTE_TYPE,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._compute_type = compute_type
        self._model: Optional[WhisperModel] = None

    def load(self, progress_cb: Optional[Callable[[str], None]] = None) -> None:
        """Load (and download if needed) the Whisper model into memory."""
        try:
            _cb(progress_cb, f"Loading model '{self._model_name}'...")
            self._model = WhisperModel(
                self._model_name,
                device=self._device,
                compute_type=self._compute_type,
            )
            _cb(progress_cb, "Model ready.")
        except Exception as e:
            raise RuntimeError(f"Model load failed ({self._model_name}): {e}") from e

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = TranscriptionDefaults.DEFAULT_LANGUAGE,
        beam_size: int = TranscriptionDefaults.BEAM_SIZE,
        vad_filter: bool = TranscriptionDefaults.VAD_FILTER,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> list[Segment]:
        """Transcribe an audio file and return a list of word-timestamped segments.

        Raises RuntimeError when the model is not loaded or transcription fails.
        """
        try:
            if self._model is None:
                raise RuntimeError("Call load() before transcribe().")
            if not os.path.isfile(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            return list(self._iter_segments(audio_path, language, beam_size, vad_filter, progress_cb))
        except (RuntimeError, FileNotFoundError):
            raise
        except Exception as e:
            raise RuntimeError(f"Transcription failed: {e}") from e

    def is_loaded(self) -> bool:
        """Return True when a model is currently held in memory."""
        return self._model is not None

    def unload(self) -> None:
        """Release the model from memory."""
        try:
            self._model = None
        except Exception:
            pass

    def _iter_segments(
        self,
        audio_path: str,
        language: Optional[str],
        beam_size: int,
        vad_filter: bool,
        progress_cb: Optional[Callable[[str], None]],
    ) -> Iterator[Segment]:
        """Iterate faster-whisper output and yield typed Segment dicts."""
        vad_params = {"min_silence_duration_ms": TranscriptionDefaults.VAD_MIN_SILENCE_MS}
        segments, info = self._model.transcribe(  # type: ignore[union-attr]
            audio_path,
            language=language,
            beam_size=beam_size,
            word_timestamps=TranscriptionDefaults.WORD_TIMESTAMPS,
            vad_filter=vad_filter,
            vad_parameters=vad_params,
        )
        detected = info.language if language is None else language
        for idx, seg in enumerate(segments):
            _cb(progress_cb, f"Segment {idx + 1}: [{seg.start:.1f}s → {seg.end:.1f}s]")
            words: list[WordToken] = []
            if seg.words:
                words = [
                    WordToken(word=w.word, start=w.start, end=w.end)
                    for w in seg.words
                ]
            yield Segment(
                id=idx,
                start=seg.start,
                end=seg.end,
                text=seg.text,
                words=words,
                language=detected,
            )


def _cb(fn: Optional[Callable[[str], None]], msg: str) -> None:
    """Call a progress callback safely when present."""
    try:
        if fn:
            fn(msg)
    except Exception:
        pass
