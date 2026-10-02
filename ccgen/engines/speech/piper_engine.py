# piper_engine.py - Piper text-to-speech: small ONNX voices for many languages

import json
import logging
import os
from pathlib import Path

import numpy as np
from piper import PiperVoice, SynthesisConfig
from piper.config import PiperConfig

from ccgen.engines.devices import onnx_session
from ccgen.engines.model_cache import ModelCache
from ccgen.engines.speech.base import ProgressCb, SpeechEngine, StatusCb
from ccgen.engines.speech.voice_files import ensure_piper
from ccgen.utils.callbacks import emit_status

_log = logging.getLogger(__name__)

_voices: ModelCache[tuple[PiperVoice, str]] = ModelCache("Piper voice")
# A typical line, spoken on each device at load to find the fastest one that can run the voice.
_PROBE_TEXT = "This short sentence checks how quickly speech runs on this device."


class PiperEngine(SpeechEngine):
    """Speaks with one downloaded Piper voice."""

    def load(self, status_cb: StatusCb = None, progress_cb: ProgressCb = None) -> None:
        """Download the voice on first use and open it on the fastest ONNX provider."""
        def loader() -> tuple[PiperVoice, str]:
            emit_status(status_cb, f"Preparing Piper voice {self.voice.voice_id}...")
            model_path, config_path = ensure_piper(self.voice, progress_cb)
            with open(config_path, encoding="utf-8") as fh:
                config = PiperConfig.from_dict(json.load(fh))
            # Chinese voices fetch an extra pronunciation model into download_dir on first use.
            download_dir = Path(os.path.dirname(model_path))

            def probe(session) -> None:
                list(PiperVoice(session=session, config=config, download_dir=download_dir).synthesize(_PROBE_TEXT))

            session, accelerator = onnx_session(model_path, self._device_preference, probe)
            return PiperVoice(session=session, config=config, download_dir=download_dir), accelerator.label

        self._piper, self.device_label = _voices.get_or_load((self.voice.key, self._device_preference), loader)

    def synthesize(self, text: str, speed: float = 1.0, speaker: int = 0) -> tuple[np.ndarray, int]:
        """Speak `text`; speed shortens the voice's own length scale (its tuned speaking rate)."""
        try:
            return self._speak(text, speed)
        except Exception as e:
            self._fall_back_to_cpu(e)
            return self._speak(text, speed)

    def _speak(self, text: str, speed: float) -> tuple[np.ndarray, int]:
        """One synthesis on the current session."""
        length_scale = (self._piper.config.length_scale or 1.0) / speed
        chunks = list(self._piper.synthesize(text, SynthesisConfig(length_scale=length_scale)))
        if not chunks:
            return np.zeros(0, dtype=np.float32), self._piper.config.sample_rate
        audio = np.concatenate([chunk.audio_float_array for chunk in chunks]).astype(np.float32)
        return audio, chunks[0].sample_rate
