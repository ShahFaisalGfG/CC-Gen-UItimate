# base.py — abstract contract for caption (transcription) engines

from abc import ABC, abstractmethod
from typing import Callable, Optional

import numpy as np

from ccgen.core import Segment


class CaptionEngine(ABC):
    """Common interface every caption engine (whisper, future engines) must implement."""

    @abstractmethod
    def load(
        self,
        progress_cb: Optional[Callable[[str], None]] = None,
        progress_num_cb: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Load (and download if needed) the engine's model into memory."""

    @abstractmethod
    def transcribe(
        self,
        audio: str | np.ndarray,
        language: Optional[str],
        beam_size: int,
        vad_filter: bool,
        progress_cb: Optional[Callable[[str], None]] = None,
        segment_cb: Optional[Callable[[Segment], None]] = None,
        progress_num_cb: Optional[Callable[[int, int], None]] = None,
    ) -> list[Segment]:
        """Transcribe a media file path or 16 kHz mono float32 samples into word-timestamped segments."""
