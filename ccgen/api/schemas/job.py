# job.py - request contract for starting pipeline jobs

from typing import Optional

from pydantic import BaseModel, Field

from ccgen.config.defaults import (
    ComputeDefaults,
    ModelDefaults,
    OutputDefaults,
    TranscriptionDefaults,
    TranslationDefaults,
    TransliterationDefaults,
)


class JobConfig(BaseModel):
    """Request body to start a transcription/translation/transliteration job."""

    input_path: str
    output_dir: Optional[str] = None
    model_name: str = ModelDefaults.DEFAULT_MODEL
    device: str = ComputeDefaults.DEFAULT_DEVICE
    compute_type: str = ComputeDefaults.DEFAULT_COMPUTE_TYPE
    language: Optional[str] = None
    translate: bool = TranslationDefaults.TRANSLATE_ENABLED
    source_lang: str = TranslationDefaults.DEFAULT_SOURCE_LANG
    target_lang: str = TranslationDefaults.DEFAULT_TARGET_LANG
    emit_srt: bool = OutputDefaults.FORMAT_SRT
    emit_vtt: bool = OutputDefaults.FORMAT_VTT
    emit_lrc: bool = OutputDefaults.FORMAT_LRC
    emit_ass: bool = OutputDefaults.FORMAT_ASS
    emit_sbv: bool = OutputDefaults.FORMAT_SBV
    max_line_length: int = Field(
        OutputDefaults.MAX_LINE_LENGTH,
        ge=OutputDefaults.MAX_LINE_LENGTH_RANGE[0], le=OutputDefaults.MAX_LINE_LENGTH_RANGE[1],
    )
    max_lines: int = Field(
        OutputDefaults.MAX_LINES, ge=OutputDefaults.MAX_LINES_RANGE[0], le=OutputDefaults.MAX_LINES_RANGE[1],
    )
    beam_size: int = TranscriptionDefaults.BEAM_SIZE
    vad_filter: bool = TranscriptionDefaults.VAD_FILTER
    transliterate: bool = TransliterationDefaults.ENABLED
    translit_source: str = TransliterationDefaults.DEFAULT_SOURCE
    translit_target: str = TransliterationDefaults.DEFAULT_TARGET
    translit_input: str = TransliterationDefaults.INPUT_SOURCE
    translit_engine: str = TransliterationDefaults.DEFAULT_ENGINE
