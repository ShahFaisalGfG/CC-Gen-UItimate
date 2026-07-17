# base.py — abstract contract for translation engines

from abc import ABC, abstractmethod
from typing import Callable, Optional

from ccgen.core import Segment, TranslatedSegment


class TranslationEngine(ABC):
    """Common interface every translation engine (argos, future engines) must implement."""

    @abstractmethod
    def ensure_model(self, progress_cb: Optional[Callable[[str], None]] = None) -> None:
        """Download and install the language pair model when not already present."""

    @abstractmethod
    def translate_segments(
        self,
        segments: list[Segment],
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> list[TranslatedSegment]:
        """Translate a segment list, preserving all timing from the source."""

    @abstractmethod
    def set_pair(self, source: str, target: str) -> None:
        """Update the source/target language codes and reset the loaded engine."""
