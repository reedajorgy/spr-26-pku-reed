#!/usr/bin/env python3

import argparse
import datetime
import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from faster_whisper import WhisperModel
from tqdm import tqdm
from zhconv import convert as zhconv_convert


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-transcribe lecture recordings to .txt files using faster-whisper (offline).",
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        required=False,
        default=None,
        help="Directory containing lecture recordings (e.g. .m4a, .wav, .mp3). Defaults to raw_materials/audio_lectures if present, otherwise lecture_recordings.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to write .txt transcripts. Defaults to mirroring structure under input-dir.",
    )
    parser.add_argument(
        "--model-size",
        type=str,
        default="medium",
        choices=["small", "medium", "large-v2"],
        help="Whisper model size to use. Default: medium.",
    )
    parser.add_argument(
        "--compute-type",
        type=str,
        default="int8",
        choices=["int8", "int8_float16", "float16", "int16", "float32"],
        help=(
            "CTranslate2 compute type. int8 is CPU-safe; int8_float16 is faster where supported. "
            "Use float16/float32 for maximum accuracy if you can wait."
        ),
    )
    parser.add_argument(
        "--language",
        type=str,
        default="zh",
        help="Spoken language code (ISO 639-1). Default: zh (Chinese).",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="Maximum number of audio files to transcribe in parallel. Default: 1 (sequential).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing transcript files instead of skipping them.",
    )
    parser.add_argument(
        "--include-timestamps",
        action="store_true",
        help="Include per-segment timestamps in the output .txt file.",
    )
    parser.add_argument(
        "--initial-prompt",
        type=str,
        default=None,
        help=(
            "Optional initial prompt to bias transcription (e.g. common technical terms, names, university). "
            "This can improve accuracy on domain-specific vocabulary."
        ),
    )
    parser.add_argument(
        "--extensions",
        type=str,
        default=".m4a,.wav,.mp3,.flac,.ogg",
        help="Comma-separated list of audio file extensions to include.",
    )
    return parser.parse_args()


def find_audio_files(input_dir: Path, extensions: Iterable[str]) -> List[Path]:
    normalized_exts = {ext.lower().strip() for ext in extensions if ext.strip()}
    audio_files: List[Path] = []
    for path in input_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in normalized_exts:
            audio_files.append(path)
    audio_files.sort()
    return audio_files


def resolve_output_path(audio_path: Path, input_dir: Path, output_dir: Optional[Path]) -> Path:
    relative_path = audio_path.relative_to(input_dir)
    output_directory = output_dir if output_dir is not None else input_dir
    return (output_directory / relative_path).with_suffix(".txt")


def configure_logging(log_directory: Path) -> None:
    log_directory.mkdir(parents=True, exist_ok=True)
    log_file = log_directory / "transcription.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def load_model(model_size: str, compute_type: str) -> WhisperModel:
    logging.info(
        "Loading faster-whisper model '%s' with compute_type='%s' on CPU. "
        "This may take a while the first time.",
        model_size,
        compute_type,
    )
    model = WhisperModel(
        model_size,
        device="cpu",
        compute_type=compute_type,
    )
    return model


def format_timestamp(seconds: float) -> str:
    delta = datetime.timedelta(seconds=float(seconds))
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def transcribe_with_model(
    model: WhisperModel,
    audio_path: Path,
    language: str,
    include_timestamps: bool,
    initial_prompt: Optional[str],
) -> Tuple[str, List[Tuple[str, str]]]:
    beam_size = 5
    patience = 1.0
    temperature_schedule = [0.0, 0.2, 0.4]
    chunk_length_seconds = 30

    effective_prompt = initial_prompt
    if language == "zh" and effective_prompt is None:
        effective_prompt = "简体"
    logging.info("Transcribing '%s'...", audio_path)
    segments, _ = model.transcribe(
        str(audio_path),
        language=language,
        task="transcribe",
        beam_size=beam_size,
        best_of=beam_size,
        patience=patience,
        temperature=temperature_schedule,
        vad_filter=True,
        chunk_length=chunk_length_seconds,
        condition_on_previous_text=True,
        initial_prompt=effective_prompt,
    )

    plain_text_parts: List[str] = []
    timestamped_segments: List[Tuple[str, str]] = []

    processed_segments = 0

    for segment in segments:
        raw_text = segment.text.strip()
        if not raw_text:
            continue
        text = zhconv_convert(raw_text, "zh-cn") if language == "zh" else raw_text
        plain_text_parts.append(text)
        if include_timestamps:
            start_timestamp = format_timestamp(segment.start)
            timestamped_segments.append((start_timestamp, text))

        processed_segments += 1
        if processed_segments % 25 == 0:
            logging.info(
                "Processed segment %d (start %s)",
                processed_segments,
                format_timestamp(segment.start),
            )

    full_plain_text = "\n".join(plain_text_parts)
    return full_plain_text, timestamped_segments


def write_transcript(
    output_path: Path,
    plain_text: str,
    timestamped_segments: List[Tuple[str, str]],
    include_timestamps: bool,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        if include_timestamps and timestamped_segments:
            for start, text in timestamped_segments:
                file.write(f"[{start}] {text}\n")
        else:
            file.write(plain_text)


def transcribe_audio_file(
    audio_path: Path,
    output_path: Path,
    model_size: str = "medium",
    compute_type: str = "int8",
    language: str = "zh",
    include_timestamps: bool = False,
    initial_prompt: Optional[str] = None,
) -> None:
    """
    Transcribe a single audio file to the provided output path using the same tuned settings
    as the batch CLI. This is intended for use by higher-level runners.
    """
    logging.info("Starting transcription for '%s' -> '%s'", audio_path, output_path)
    start_time = datetime.datetime.now()

    model = load_model(model_size=model_size, compute_type=compute_type)
    plain_text, timestamped_segments = transcribe_with_model(
        model=model,
        audio_path=audio_path,
        language=language,
        include_timestamps=include_timestamps,
        initial_prompt=initial_prompt,
    )
    write_transcript(
        output_path=output_path,
        plain_text=plain_text,
        timestamped_segments=timestamped_segments,
        include_timestamps=include_timestamps,
    )

    elapsed = datetime.datetime.now() - start_time
    logging.info("Finished transcription for '%s' in %s", audio_path, elapsed)


def transcribe_single_file(
    audio_path: Path,
    input_dir: Path,
    output_dir: Optional[Path],
    model_size: str,
    compute_type: str,
    language: str,
    include_timestamps: bool,
    initial_prompt: Optional[str],
    overwrite: bool,
) -> Tuple[Path, bool, Optional[str]]:
    output_path = resolve_output_path(audio_path, input_dir, output_dir)
    if output_path.exists() and not overwrite:
        message = "Transcript already exists. Skipping (use --overwrite to regenerate)."
        logging.info("%s -> %s", audio_path, message)
        return audio_path, False, None

    try:
        model = load_model(model_size=model_size, compute_type=compute_type)
        plain_text, timestamped_segments = transcribe_with_model(
            model=model,
            audio_path=audio_path,
            language=language,
            include_timestamps=include_timestamps,
            initial_prompt=initial_prompt,
        )
        write_transcript(
            output_path=output_path,
            plain_text=plain_text,
            timestamped_segments=timestamped_segments,
            include_timestamps=include_timestamps,
        )
        logging.info("Finished '%s' -> '%s'", audio_path, output_path)
        return audio_path, True, None
    except Exception as error:  # noqa: BLE001
        logging.exception("Error transcribing '%s': %s", audio_path, error)
        return audio_path, False, str(error)


def _default_input_dir(repo_root: Path) -> Path:
    raw_dir = repo_root / "raw_materials" / "audio_lectures"
    if raw_dir.is_dir():
        return raw_dir
    legacy_dir = repo_root / "lecture_recordings"
    return legacy_dir


def main() -> None:
    args = parse_arguments()

    repo_root = Path(__file__).resolve().parents[2]
    if args.input_dir is not None:
        input_dir = Path(args.input_dir).expanduser().resolve()
    else:
        input_dir = _default_input_dir(repo_root)

    if not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist or is not a directory: {input_dir}")

    output_dir = None
    if args.output_dir is not None:
        output_dir = Path(args.output_dir).expanduser().resolve()

    log_directory = output_dir if output_dir is not None else input_dir
    configure_logging(log_directory=log_directory)

    extensions = [ext if ext.startswith(".") else f".{ext}" for ext in args.extensions.split(",")]
    audio_files = find_audio_files(input_dir=input_dir, extensions=extensions)
    if not audio_files:
        logging.warning("No audio files found in %s with extensions %s", input_dir, extensions)
        return

    logging.info("Found %d audio files to process.", len(audio_files))

    max_workers = max(int(args.max_workers), 1)
    model_size = args.model_size
    compute_type = args.compute_type
    language = args.language
    include_timestamps = bool(args.include_timestamps)
    initial_prompt = args.initial_prompt
    overwrite = bool(args.overwrite)

    if max_workers == 1:
        successful = 0
        with tqdm(total=len(audio_files), desc="Transcribing", unit="file") as progress_bar:
            for audio_path in audio_files:
                start_time = datetime.datetime.now()
                model = load_model(model_size=model_size, compute_type=compute_type)
                plain_text, timestamped_segments = transcribe_with_model(
                    model=model,
                    audio_path=audio_path,
                    language=language,
                    include_timestamps=include_timestamps,
                    initial_prompt=initial_prompt,
                )
                output_path = resolve_output_path(audio_path, input_dir, output_dir)
                if output_path.exists() and not overwrite:
                    logging.info(
                        "Transcript already exists for '%s'. Skipping (use --overwrite to regenerate).",
                        audio_path,
                    )
                else:
                    write_transcript(
                        output_path=output_path,
                        plain_text=plain_text,
                        timestamped_segments=timestamped_segments,
                        include_timestamps=include_timestamps,
                    )
                    successful += 1

                elapsed = datetime.datetime.now() - start_time
                logging.info("Completed '%s' in %s.", audio_path, elapsed)
                progress_bar.update(1)

        logging.info("Completed transcription. Successful: %d / %d", successful, len(audio_files))
        return

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                transcribe_single_file,
                audio_path,
                input_dir,
                output_dir,
                model_size,
                compute_type,
                language,
                include_timestamps,
                initial_prompt,
                overwrite,
            ): audio_path
            for audio_path in audio_files
        }

        successful = 0
        with tqdm(total=len(audio_files), desc="Transcribing (parallel)", unit="file") as progress_bar:
            for future in as_completed(futures):
                audio_path = futures[future]
                _, ok, error_message = future.result()
                if ok:
                    successful += 1
                else:
                    if error_message is not None:
                        logging.error("Failed to transcribe '%s': %s", audio_path, error_message)
                progress_bar.update(1)

    logging.info("Completed transcription. Successful: %d / %d", successful, len(audio_files))


if __name__ == "__main__":
    main()

