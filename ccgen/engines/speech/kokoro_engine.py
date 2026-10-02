# kokoro_engine.py - Kokoro text-to-speech: one shared 82M-parameter ONNX model, many stock voices

import logging

import numpy as np
from kokoro_onnx import Kokoro

from ccgen.engines.devices import onnx_session
from ccgen.engines.model_cache import ModelCache
from ccgen.engines.speech.base import ProgressCb, SpeechEngine, StatusCb
from ccgen.engines.speech.voice_files import ensure_kokoro
from ccgen.utils.callbacks import emit_status

_log = logging.getLogger(__name__)

_models: ModelCache[tuple[Kokoro, str]] = ModelCache("Kokoro")
# Kokoro accepts speeds in this range; faster requests are clamped to its maximum.
_MAX_SPEED = 2.0
# A typical line, spoken on each device at load to find the fastest one that can run the voice.
_PROBE_TEXT = "This short sentence checks how quickly speech runs on this device."


class KokoroEngine(SpeechEngine):
    """Speaks with one Kokoro stock voice."""

    def load(self, status_cb: StatusCb = None, progress_cb: ProgressCb = None) -> None:
        """Download the shared model on first use and open it on the fastest ONNX provider."""
        def loader() -> tuple[Kokoro, str]:
            emit_status(status_cb, "Preparing Kokoro...")
            model_path, voices_path = ensure_kokoro(progress_cb)

            def probe(session) -> None:
                Kokoro.from_session(session, voices_path).create(
                    _PROBE_TEXT, voice=self.voice.voice_id, lang=self.voice.locale,
                )

            session, accelerator = onnx_session(model_path, self._device_preference, probe)
            return Kokoro.from_session(session, voices_path), accelerator.label

        self._kokoro, self.device_label = _models.get_or_load(self._device_preference, loader)

    def synthesize(self, text: str, speed: float = 1.0, speaker: int = 0) -> tuple[np.ndarray, int]:
        """Speak `text` in the configured voice and accent."""
        try:
            return self._speak(text, speed)
        except Exception as e:
            self._fall_back_to_cpu(e)
            return self._speak(text, speed)

    def _speak(self, text: str, speed: float) -> tuple[np.ndarray, int]:
        """One synthesis on the current session."""
        samples, rate = self._kokoro.create(
            text, voice=self.voice.voice_id, speed=min(speed, _MAX_SPEED), lang=self.voice.locale,
        )
        return np.asarray(samples, dtype=np.float32), rate
