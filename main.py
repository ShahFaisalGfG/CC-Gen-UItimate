# main.py — CLI entry point for CC-Gen-Ultimate (core testing without UI)

import argparse
import os
import sys

from ccgen.config.defaults import ModelDefaults, TranslationDefaults
from ccgen.core.pipeline import Pipeline, PipelineConfig


def main() -> None:
    """Parse CLI arguments and run the subtitle generation pipeline."""
    args = _parse_args()
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
        help="Whisper model size (default: base)",
    )
    p.add_argument(
        "--device",
        default="cpu",
        choices=["cpu", "cuda"],
        help="Compute device (default: cpu)",
    )
    p.add_argument(
        "--compute-type",
        default="int8",
        choices=["int8", "float16", "float32"],
        help="CTranslate2 compute type (default: int8)",
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
        "--vtt",
        action="store_true",
        help="Also emit a WebVTT (.vtt) subtitle file.",
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
    return PipelineConfig(
        input_path=os.path.abspath(args.input),
        output_dir=args.output_dir,
        model_name=args.model,
        device=args.device,
        compute_type=args.compute_type,
        language=args.language,
        translate=args.translate,
        target_lang=args.target_lang,
        emit_srt=True,
        emit_vtt=args.vtt,
    )


def _print_progress(msg: str) -> None:
    """Print a pipeline status message to stdout."""
    print(f"  {msg}")


if __name__ == "__main__":
    main()
