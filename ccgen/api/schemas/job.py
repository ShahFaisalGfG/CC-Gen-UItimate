# job.py — request/response contracts for starting and tracking pipeline jobs

from typing import Optional

from pydantic import BaseModel

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
    beam_size: int = TranscriptionDefaults.BEAM_SIZE
    vad_filter: bool = TranscriptionDefaults.VAD_FILTER
    transliterate: bool = TransliterationDefaults.ENABLED
    translit_source: str = TransliterationDefaults.DEFAULT_SOURCE
    translit_target: str = TransliterationDefaults.DEFAULT_TARGET
    translit_input: str = TransliterationDefaults.INPUT_SOURCE
    translit_engine: str = TransliterationDefaults.DEFAULT_ENGINE


class JobStatus(BaseModel):
    """Snapshot of a job's current state, for polling clients."""

    job_id: str
    busy: bool
    success: Optional[bool] = None
    error: Optional[str] = None
    output_files: list[str] = []
