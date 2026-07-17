# base.py — abstract contract for transliteration engines

from abc import ABC, abstractmethod
from typing import Callable, Optional, Union

from ccgen.core import Segment, TranslatedSegment, TransliteratedSegment


class TransliterationEngine(ABC):
    """Common interface every transliteration engine (rule, neural) must implement."""

    @abstractmethod
    def transliterate_segments(
        self,
        segments: Union[list[Segment], list[TranslatedSegment]],
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> list[TransliteratedSegment]:
        """Transliterate a segment list between scripts, preserving timing."""
