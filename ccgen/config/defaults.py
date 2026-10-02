# defaults.py - application defaults and supported options for CC-Gen-Ultimate

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
    SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large-v3-turbo", "large-v3"]
    MODEL_SIZES_MB: dict[str, int] = {
        "tiny": 75,
        "base": 145,
        "small": 466,
        "medium": 1500,
        "large-v3-turbo": 1620,
        "large-v3": 3000,
    }
    MODEL_NOTES: dict[str, str] = {
        "tiny": "fastest, rough drafts",
        "base": "fast, good for clear speech",
        "small": "balanced speed and accuracy",
        "medium": "accurate, slow on CPU",
        "large-v3-turbo": "near-best accuracy, much faster than large",
        "large-v3": "best accuracy, slowest",
    }


class ModelRepos:
    """Hugging Face repo ids for every downloadable model.

    Shared by the engines that load them, the cache-status checks, and the Manage Models catalog,
    so adding a model means editing this one place.
    """

    WHISPER: dict[str, str] = {
        "tiny": "Systran/faster-whisper-tiny",
        "base": "Systran/faster-whisper-base",
        "small": "Systran/faster-whisper-small",
        "medium": "Systran/faster-whisper-medium",
        "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
        "large-v3": "Systran/faster-whisper-large-v3",
    }
    M2M100_TOKENIZER = "Mavkif/m2m100_rup_tokenizer_both"
    M2M100: dict[tuple[str, str], str] = {
        ("ur", "roman"): "Mavkif/m2m100_rup_ur_to_rur",
        ("roman", "ur"): "Mavkif/m2m100_rup_rur_to_ur",
    }
    REKHTA = "rekhtalabs/hi-2-ur-translit"


class ComputeDefaults:
    """CTranslate2 device and compute type defaults.

    "auto" picks an NVIDIA GPU when CUDA is usable and falls back to the CPU otherwise; the
    "auto" compute type resolves to float16 on a GPU and int8 on a CPU.
    """

    DEVICE_AUTO = "auto"
    COMPUTE_AUTO = "auto"
    DEFAULT_DEVICE = DEVICE_AUTO
    DEFAULT_COMPUTE_TYPE = COMPUTE_AUTO
    SUPPORTED_DEVICES = [DEVICE_AUTO, "cpu", "cuda"]
    SUPPORTED_COMPUTE_TYPES = [COMPUTE_AUTO, "int8", "float16", "float32"]
    DEVICES: list[tuple[str, str]] = [
        ("Automatic (GPU when available)", DEVICE_AUTO),
        ("CPU", "cpu"),
        ("NVIDIA GPU (CUDA)", "cuda"),
    ]


class TranscriptionDefaults:
    """faster-whisper transcription defaults."""

    DEFAULT_LANGUAGE: str | None = None
    WORD_TIMESTAMPS = True
    BEAM_SIZE = 5
    VAD_FILTER = True
    VAD_MIN_SILENCE_MS = 500
    # Conditioning each window on the previous one lets a single misheard phrase repeat for
    # minutes on long files; turning it off trades a little stylistic consistency for robustness.
    CONDITION_ON_PREVIOUS_TEXT = False
    # Skips silent stretches longer than this when a window looks hallucinated (needs word timestamps).
    HALLUCINATION_SILENCE_S = 2.0
    # Language detection votes over this many 30 s windows, so a music or silent intro can't
    # decide the language for the whole file on its own.
    LANGUAGE_DETECTION_SEGMENTS = 3


class TranslationDefaults:
    """argostranslate defaults."""

    DEFAULT_SOURCE_LANG = "auto"
    DEFAULT_TARGET_LANG = "en"
    TRANSLATE_ENABLED = False


class OutputDefaults:
    """Subtitle output format and cue layout defaults."""

    FORMAT_SRT = True
    FORMAT_VTT = False
    FORMAT_LRC = False
    FORMAT_ASS = False
    FORMAT_SBV = False
    # Empty means "next to each input file".
    DIRECTORY = ""
    MAX_LINE_LENGTH = 42
    MAX_LINE_LENGTH_RANGE = (20, 80)
    MAX_LINES = 2
    MAX_LINES_RANGE = (1, 3)
    MIN_DURATION_MS = 500
    # A cue is closed early once it runs this long, even when it still has room for more text.
    MAX_CUE_DURATION_S = 7.0
    # A pause between two words at least this long starts a new cue.
    CUE_PAUSE_SPLIT_S = 0.8
    # Scripts written without spaces between words get a shorter line limit (Netflix guidance).
    NO_SPACE_LANGUAGES = frozenset({"zh", "ja", "th", "my", "lo", "km"})
    NO_SPACE_MAX_LINE_LENGTH = 16


class AudioDefaults:
    """ffmpeg audio extraction defaults."""

    SAMPLE_RATE = 16000
    CHANNELS = 1
    AUDIO_FORMAT = "wav"


class LoggingDefaults:
    """Logging preferences: "critical" keeps errors only, "all" records everything."""

    ENABLE_LOGS = True
    DEFAULT_LOG_LEVEL = "critical"
    SUPPORTED_LOG_LEVELS = ["critical", "all"]
    LOG_FILE_NAME = "ccgen.log"
    MAX_LOG_BYTES = 1_000_000
    LOG_BACKUP_COUNT = 3


class LanguageOptions:
    """Language lists for transcription and translation UI dropdowns."""

    TRANSCRIPTION: list[tuple[str, str | None]] = [
        ("Auto-detect", None),
        ("Arabic", "ar"),
        ("Chinese", "zh"),
        ("English", "en"),
        ("French", "fr"),
        ("German", "de"),
        ("Hindi", "hi"),
        ("Japanese", "ja"),
        ("Korean", "ko"),
        ("Portuguese", "pt"),
        ("Russian", "ru"),
        ("Spanish", "es"),
        ("Turkish", "tr"),
        ("Urdu", "ur"),
    ]

    TRANSLATION_TARGETS: list[tuple[str, str]] = [
        ("Arabic", "ar"),
        ("English", "en"),
        ("French", "fr"),
        ("German", "de"),
        ("Hindi", "hi"),
        ("Portuguese", "pt"),
        ("Russian", "ru"),
        ("Spanish", "es"),
        ("Turkish", "tr"),
        ("Urdu", "ur"),
    ]


class TransliterationDefaults:
    """Transliteration scheme and engine defaults."""

    DEFAULT_SOURCE = "roman"
    DEFAULT_TARGET = "ur"
    ENABLED = False
    INPUT_SOURCE = "transcription"

    ENGINE_RULE = "rule"
    ENGINE_NEURAL = "neural"
    DEFAULT_ENGINE = ENGINE_RULE

    ENGINES: list[tuple[str, str]] = [
        ("Rule-based (fast, offline)", ENGINE_RULE),
        ("Neural (higher quality)", ENGINE_NEURAL),
    ]

    SCHEMES: list[tuple[str, str]] = [
        ("Roman / Latin",      "roman"),
        ("Urdu (Nastaliq)",    "ur"),
        ("Hindi (Devanagari)", "hi"),
        ("Bengali",            "bn"),
        ("Gujarati",           "gu"),
        ("Punjabi (Gurmukhi)", "pa"),
        ("Tamil",              "ta"),
        ("Telugu",             "te"),
        ("Kannada",            "kn"),
        ("Malayalam",          "ml"),
        ("Odia",               "or"),
        ("Sinhala",            "si"),
        ("Thai",               "th"),
        ("Burmese",            "my"),
    ]


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
            "directory": OutputDefaults.DIRECTORY,
            "srt": OutputDefaults.FORMAT_SRT,
            "vtt": OutputDefaults.FORMAT_VTT,
            "lrc": OutputDefaults.FORMAT_LRC,
            "ass": OutputDefaults.FORMAT_ASS,
            "sbv": OutputDefaults.FORMAT_SBV,
            "max_line_length": OutputDefaults.MAX_LINE_LENGTH,
            "max_lines": OutputDefaults.MAX_LINES,
        },
        "logging": {
            "enable_logs": LoggingDefaults.ENABLE_LOGS,
            "log_level": LoggingDefaults.DEFAULT_LOG_LEVEL,
        },
        "transliteration": {
            "enabled": TransliterationDefaults.ENABLED,
            "source": TransliterationDefaults.DEFAULT_SOURCE,
            "target": TransliterationDefaults.DEFAULT_TARGET,
            "input_source": TransliterationDefaults.INPUT_SOURCE,
            "engine": TransliterationDefaults.DEFAULT_ENGINE,
        },
        "ui": {
            "theme": "system",
        },
    }
