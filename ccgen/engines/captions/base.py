# base.py — abstract contract for caption (transcription) engines

from abc import ABC, abstractmethod
from typing import Callable, Optional

from ccgen.core import Segment


class CaptionEngine(ABC):
    """Common interface every caption engine (whisper, future engines) must implement."""

    @abstractmethod
    def load(self, progress_cb: Optional[Callable[[str], None]] = None) -> None:
        """Load (and download if needed) the engine's model into memory."""

    @abstractmethod
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str],
        beam_size: int,
        vad_filter: bool,
        progress_cb: Optional[Callable[[str], None]] = None,
        segment_cb: Optional[Callable[[Segment], None]] = None,
    ) -> list[Segment]:
        """Transcribe an audio file and return word-timestamped segments."""
