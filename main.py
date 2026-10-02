# main.py - CLI entry point for CC-Gen-Ultimate (core testing without UI)

import argparse
import os
import sys

from ccgen.config.defaults import (
    ComputeDefaults,
    ModelDefaults,
    OutputDefaults,
    TranslationDefaults,
    TransliterationDefaults,
)
from ccgen.utils.logging import configure_logging
from ccgen.core.pipeline import Pipeline, PipelineConfig


def main() -> None:
    """Parse CLI arguments and run the subtitle generation pipeline."""
    args = _parse_args()
    configure_logging(enabled=False)
    config = _build_config(args)
    pipeline = Pipeline(config)
    try:
        pipeline.prepare(progress_cb=_print_progress)
    except RuntimeError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    result = pipeline.run(progress_cb=_print_progress)
    if not result.success:
        print(f"[ERROR] {result.error}", file=sys.stderr)
        sys.exit(1)

    print(f"\nDetected language : {result.detected_language}")
    print(f"Segments          : {len(result.segments)}")
    print("Output files:")
    for f in result.output_files:
        print(f"  {f}")


def _parse_args() -> argparse.Namespace:
    """Build and return the parsed CLI argument namespace."""
    p = argparse.ArgumentParser(
        prog="ccgen",
        description="Transcribe and generate subtitles from video/audio files.",
    )
    p.add_argument("input", help="Path to input video or audio file")
    p.add_argument(
        "--model",
        default=ModelDefaults.DEFAULT_MODEL,
        choices=ModelDefaults.SUPPORTED_MODELS,
        help=f"Whisper model (default: {ModelDefaults.DEFAULT_MODEL})",
    )
    p.add_argument(
        "--device",
        default=ComputeDefaults.DEFAULT_DEVICE,
        choices=ComputeDefaults.SUPPORTED_DEVICES,
        help="Compute device; auto uses a CUDA GPU when available (default: auto)",
    )
    p.add_argument(
        "--compute-type",
        default=ComputeDefaults.DEFAULT_COMPUTE_TYPE,
        choices=ComputeDefaults.SUPPORTED_COMPUTE_TYPES,
        help="CTranslate2 compute type; auto picks float16 on GPU, int8 on CPU (default: auto)",
    )
    p.add_argument(
        "--language",
        default=None,
        help="Source language code e.g. 'en', 'ar'. Default: auto-detect.",
    )
    p.add_argument(
        "--translate",
        action="store_true",
        help="Translate transcription to the target language.",
    )
    p.add_argument(
        "--target-lang",
        default=TranslationDefaults.DEFAULT_TARGET_LANG,
        help="Translation target language code (default: en).",
    )
    p.add_argument(
        "--formats",
        default="srt",
        help="Comma-separated subtitle formats: srt, vtt, ass, sbv, lrc (default: srt).",
    )
    p.add_argument(
        "--vtt",
        action="store_true",
        help="Also emit a WebVTT (.vtt) subtitle file (same as adding vtt to --formats).",
    )
    p.add_argument(
        "--max-line-length",
        type=int,
        default=OutputDefaults.MAX_LINE_LENGTH,
        help=f"Characters per subtitle line (default: {OutputDefaults.MAX_LINE_LENGTH}).",
    )
    p.add_argument(
        "--max-lines",
        type=int,
        default=OutputDefaults.MAX_LINES,
        help=f"Lines per subtitle cue (default: {OutputDefaults.MAX_LINES}).",
    )
    p.add_argument(
        "--transliterate",
        action="store_true",
        help="Transliterate the transcription (or translation) into another script.",
    )
    p.add_argument(
        "--translit-source",
        default=TransliterationDefaults.DEFAULT_SOURCE,
        help="Transliteration source scheme code (default: roman).",
    )
    p.add_argument(
        "--translit-target",
        default=TransliterationDefaults.DEFAULT_TARGET,
        help="Transliteration target scheme code (default: ur).",
    )
    p.add_argument(
        "--translit-input",
        default=TransliterationDefaults.INPUT_SOURCE,
        choices=["transcription", "translation"],
        help="Text to transliterate from (default: transcription).",
    )
    p.add_argument(
        "--translit-engine",
        default=TransliterationDefaults.DEFAULT_ENGINE,
        choices=[TransliterationDefaults.ENGINE_RULE, TransliterationDefaults.ENGINE_NEURAL],
        help="Transliteration engine to use (default: rule).",
    )
    p.add_argument(
        "--output-dir",
        default=None,
        help="Directory for output subtitle files (default: same dir as input).",
    )
    return p.parse_args()


def _build_config(args: argparse.Namespace) -> PipelineConfig:
    """Validate CLI args and construct a PipelineConfig. Exits on bad input."""
    if not os.path.isfile(args.input):
        print(f"[ERROR] File not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    formats = {f.strip().lower() for f in args.formats.split(",") if f.strip()}
    if args.vtt:
        formats.add("vtt")
    unknown = formats - {"srt", "vtt", "ass", "sbv", "lrc"}
    if unknown or not formats:
        print(f"[ERROR] Unknown or missing formats: {', '.join(sorted(unknown)) or 'none'}", file=sys.stderr)
        sys.exit(1)
    return PipelineConfig(
        input_path=os.path.abspath(args.input),
        output_dir=args.output_dir,
        model_name=args.model,
        device=args.device,
        compute_type=args.compute_type,
        language=args.language,
        translate=args.translate,
        target_lang=args.target_lang,
        emit_srt="srt" in formats,
        emit_vtt="vtt" in formats,
        emit_ass="ass" in formats,
        emit_sbv="sbv" in formats,
        emit_lrc="lrc" in formats,
        max_line_length=args.max_line_length,
        max_lines=args.max_lines,
        transliterate=args.transliterate,
        translit_source=args.translit_source,
        translit_target=args.translit_target,
        translit_input=args.translit_input,
        translit_engine=args.translit_engine,
    )


def _print_progress(msg: str) -> None:
    """Print a pipeline status message to stdout."""
    print(f"  {msg}")


if __name__ == "__main__":
    main()
