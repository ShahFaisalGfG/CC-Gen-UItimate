# core — shared data structures flowing through the pipeline

from typing import TypedDict


class WordToken(TypedDict):
    """A single transcribed word with its start/end timestamps in seconds."""

    word: str
    start: float
    end: float


class Segment(TypedDict):
    """A transcription segment containing text, timing, and per-word tokens."""

    id: int
    start: float
    end: float
    text: str
    words: list[WordToken]
    language: str


class TranslatedSegment(TypedDict):
    """A translated segment that preserves original timing from transcription."""

    id: int
    start: float
    end: float
    original: str
    translated: str
    language: str


__all__ = ["WordToken", "Segment", "TranslatedSegment"]
