# defaults.py — application defaults and supported options for CC-Gen-Ultimate

from typing import Any


class AppInfo:
    """Application metadata."""

    APP_NAME = "CC-Gen-Ultimate"
    APP_VERSION = "1.0.0"
    APP_AUTHOR = "Shah Faisal"
    APP_DESCRIPTION = "Offline video/audio transcription and subtitle generation"


class ModelDefaults:
    """Whisper model selection defaults."""

    DEFAULT_MODEL = "base"
    SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
    MODEL_SIZES_MB: dict[str, int] = {
        "tiny": 75,
        "base": 145,
        "small": 466,
        "medium": 1500,
        "large-v3": 3000,
    }


class ComputeDefaults:
    """CTranslate2 compute type defaults."""

    DEFAULT_DEVICE = "cpu"
    DEFAULT_COMPUTE_TYPE = "int8"
    SUPPORTED_DEVICES = ["cpu", "cuda"]
    SUPPORTED_COMPUTE_TYPES = ["int8", "float16", "float32"]


class TranscriptionDefaults:
    """faster-whisper transcription defaults."""

    DEFAULT_LANGUAGE: str | None = None
    WORD_TIMESTAMPS = True
    BEAM_SIZE = 5
    VAD_FILTER = True
    VAD_MIN_SILENCE_MS = 500


class TranslationDefaults:
    """argostranslate defaults."""

    DEFAULT_SOURCE_LANG = "auto"
    DEFAULT_TARGET_LANG = "en"
    TRANSLATE_ENABLED = False


class OutputDefaults:
    """Subtitle output format defaults."""

    FORMAT_SRT = True
    FORMAT_VTT = False
    MAX_LINE_LENGTH = 42
    MAX_LINES = 2
    MIN_DURATION_MS = 500


class AudioDefaults:
    """ffmpeg audio extraction defaults."""

    SAMPLE_RATE = 16000
    CHANNELS = 1
    AUDIO_FORMAT = "wav"


class LoggingDefaults:
    """Logging preferences."""

    ENABLE_LOGS = True
    DEFAULT_LOG_LEVEL = "critical"
    SUPPORTED_LOG_LEVELS = ["critical", "all"]


def get_default_settings() -> dict[str, Any]:
    """Return the complete default settings dictionary."""
    return {
        "model": {
            "name": ModelDefaults.DEFAULT_MODEL,
            "device": ComputeDefaults.DEFAULT_DEVICE,
            "compute_type": ComputeDefaults.DEFAULT_COMPUTE_TYPE,
        },
        "transcription": {
            "language": TranscriptionDefaults.DEFAULT_LANGUAGE,
            "word_timestamps": TranscriptionDefaults.WORD_TIMESTAMPS,
            "beam_size": TranscriptionDefaults.BEAM_SIZE,
            "vad_filter": TranscriptionDefaults.VAD_FILTER,
        },
        "translation": {
            "enabled": TranslationDefaults.TRANSLATE_ENABLED,
            "source_lang": TranslationDefaults.DEFAULT_SOURCE_LANG,
            "target_lang": TranslationDefaults.DEFAULT_TARGET_LANG,
        },
        "output": {
            "srt": OutputDefaults.FORMAT_SRT,
            "vtt": OutputDefaults.FORMAT_VTT,
            "max_line_length": OutputDefaults.MAX_LINE_LENGTH,
            "max_lines": OutputDefaults.MAX_LINES,
        },
        "logging": {
            "enable_logs": LoggingDefaults.ENABLE_LOGS,
            "log_level": LoggingDefaults.DEFAULT_LOG_LEVEL,
        },
    }
