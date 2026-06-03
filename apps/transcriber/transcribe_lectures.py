#!/usr/bin/env python3

import argparse
import datetime
import hashlib
import logging
import os
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from faster_whisper import WhisperModel
from tqdm import tqdm
from zhconv import convert as zhconv_convert

from apps.transcriber.reconcile_transcripts import ReconcileResult, reconcile_three_transcripts, reconcile_two_transcripts


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-transcribe lecture recordings to .txt files using faster-whisper (offline).",
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        required=False,
        default=None,
        help=(
            "Directory containing lecture recordings (e.g. .m4a, .wav, .mp3). "
            "Defaults to raw_materials/audio_lectures if present, otherwise lecture_recordings."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help=(
            "Directory to write .txt transcripts (legacy). "
            "Prefer --first-pass-dir for multi-run workflows. "
            "Defaults to raw_materials/first_pass_transcripts when omitted."
        ),
    )
    parser.add_argument(
        "--first-pass-dir",
        type=str,
        default=None,
        help=(
            "Directory to write first-pass transcripts. Default: raw_materials/first_pass_transcripts "
            "(mirrors the audio directory structure)."
        ),
    )
    parser.add_argument(
        "--final-dir",
        type=str,
        default=None,
        help=(
            "Directory to write final reconciled transcripts. Default: raw_materials/final_transcripts "
            "(mirrors the audio directory structure)."
        ),
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of transcription runs per audio file. Default: 1.",
    )
    parser.add_argument(
        "--queue-file",
        type=str,
        default=None,
        help=(
            "Optional path to a queue file listing audio paths to process (one per line). "
            "Lines may be absolute paths or paths relative to --input-dir. "
            "Blank lines and lines starting with # are ignored."
        ),
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip audio files that already have a final transcript (unless --overwrite is set).",
    )
    parser.add_argument(
        "--shuffle",
        action="store_true",
        help="Shuffle the processing order (useful for long unattended runs).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of audio files to process from the queue/scan.",
    )
    parser.add_argument(
        "--power",
        type=str,
        default=None,
        choices=["low", "medium", "high"],
        help=(
            "CPU-only power preset that sets --max-workers and --cpu-threads unless explicitly provided. "
            "Use this for long runs where you want a simple 'max computing power' knob."
        ),
    )
    parser.add_argument(
        "--cpu-threads",
        type=int,
        default=None,
        help="Maximum CPU threads to use per transcription process (best-effort).",
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
        default=".m4a,.wav,.mp3,.flac,.ogg,.mp4",
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


def set_cpu_thread_environment(cpu_threads: Optional[int]) -> None:
    if cpu_threads is None:
        return
    threads = max(int(cpu_threads), 1)
    for key in (
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ[key] = str(threads)


def load_model(model_size: str, compute_type: str, *, cpu_threads: Optional[int]) -> WhisperModel:
    logging.info(
        "Loading faster-whisper model '%s' with compute_type='%s' on CPU. "
        "This may take a while the first time.",
        model_size,
        compute_type,
    )
    try:
        model = WhisperModel(
            model_size,
            device="cpu",
            compute_type=compute_type,
            cpu_threads=cpu_threads,
        )
    except TypeError:
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
    temperature_schedule: Sequence[float],
) -> Tuple[str, List[Tuple[str, str]]]:
    beam_size = 5
    patience = 1.0
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
        temperature=list(temperature_schedule),
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
    cpu_threads: Optional[int] = None,
) -> None:
    """
    Transcribe a single audio file to the provided output path using the same tuned settings
    as the batch CLI. This is intended for use by higher-level runners.
    """
    logging.info("Starting transcription for '%s' -> '%s'", audio_path, output_path)
    start_time = datetime.datetime.now()

    model = load_model(model_size=model_size, compute_type=compute_type, cpu_threads=cpu_threads)
    plain_text, timestamped_segments = transcribe_with_model(
        model=model,
        audio_path=audio_path,
        language=language,
        include_timestamps=include_timestamps,
        initial_prompt=initial_prompt,
        temperature_schedule=[0.0, 0.2, 0.4],
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
    cpu_threads: Optional[int],
) -> Tuple[Path, bool, Optional[str]]:
    output_path = resolve_output_path(audio_path, input_dir, output_dir)
    if output_path.exists() and not overwrite:
        message = "Transcript already exists. Skipping (use --overwrite to regenerate)."
        logging.info("%s -> %s", audio_path, message)
        return audio_path, False, None

    try:
        model = load_model(model_size=model_size, compute_type=compute_type, cpu_threads=cpu_threads)
        plain_text, timestamped_segments = transcribe_with_model(
            model=model,
            audio_path=audio_path,
            language=language,
            include_timestamps=include_timestamps,
            initial_prompt=initial_prompt,
            temperature_schedule=[0.0, 0.2, 0.4],
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


def _default_output_dir(repo_root: Path) -> Path:
    """
    Default location for first-pass transcripts, mirroring the audio tree.
    """
    return repo_root / "raw_materials" / "first_pass_transcripts"


def _default_final_dir(repo_root: Path) -> Path:
    return repo_root / "raw_materials" / "final_transcripts"


def _compute_first_pass_path(
    audio_path: Path,
    input_dir: Path,
    first_pass_dir: Path,
    run_index: int,
) -> Path:
    relative_path = audio_path.relative_to(input_dir)
    base_path = (first_pass_dir / relative_path).with_suffix(".txt")
    return base_path.with_name(f"{base_path.stem}.run{run_index}{base_path.suffix}")


def _compute_single_pass_path(audio_path: Path, input_dir: Path, first_pass_dir: Path) -> Path:
    return resolve_output_path(audio_path, input_dir, first_pass_dir)


def _compute_final_path(audio_path: Path, input_dir: Path, final_dir: Path) -> Path:
    return resolve_output_path(audio_path, input_dir, final_dir)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_queue_file(queue_file: Path, *, input_dir: Path) -> List[Path]:
    raw_lines = queue_file.read_text(encoding="utf-8").splitlines()
    paths: List[Path] = []
    for raw in raw_lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        candidate = Path(line).expanduser()
        if not candidate.is_absolute():
            candidate = (input_dir / candidate).resolve()
        else:
            candidate = candidate.resolve()
        paths.append(candidate)
    return paths


def _temperature_schedule_for_run(run_index: int) -> List[float]:
    # Whisper decoding is often deterministic. This introduces small, bounded variation across runs.
    base = [0.0, 0.2, 0.4]
    shift = (run_index - 1) % len(base)
    return base[shift:] + base[:shift]


def _stable_seed_for_run(audio_path: Path, run_index: int) -> int:
    # Not all backends honor seeds; still useful for any downstream RNG we control.
    payload = f"{audio_path.as_posix()}::{run_index}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:4], "big", signed=False)


def process_audio_file_three_runs(
    *,
    audio_path: Path,
    input_dir: Path,
    first_pass_dir: Path,
    final_dir: Path,
    model_size: str,
    compute_type: str,
    language: str,
    include_timestamps: bool,
    initial_prompt: Optional[str],
    overwrite: bool,
    resume: bool,
    cpu_threads: Optional[int],
    write_diff_report: bool = True,
) -> Tuple[Path, bool, Optional[str], Optional[ReconcileResult]]:
    final_path = _compute_final_path(audio_path, input_dir, final_dir)
    if final_path.exists() and resume and not overwrite:
        logging.info("Final transcript exists; skipping due to --resume: %s", final_path)
        return audio_path, True, None, None

    first_pass_paths = [
        _compute_first_pass_path(audio_path, input_dir, first_pass_dir, run_index)
        for run_index in (1, 2, 3)
    ]

    texts: List[str] = []
    model: Optional[WhisperModel] = None

    for run_index, first_pass_path in enumerate(first_pass_paths, start=1):
        if first_pass_path.exists() and not overwrite:
            texts.append(_read_text(first_pass_path))
            continue

        if model is None:
            model = load_model(model_size=model_size, compute_type=compute_type, cpu_threads=cpu_threads)

        random.seed(_stable_seed_for_run(audio_path, run_index))
        temperature_schedule = _temperature_schedule_for_run(run_index)
        plain_text, timestamped_segments = transcribe_with_model(
            model=model,
            audio_path=audio_path,
            language=language,
            include_timestamps=include_timestamps,
            initial_prompt=initial_prompt,
            temperature_schedule=temperature_schedule,
        )
        write_transcript(
            output_path=first_pass_path,
            plain_text=plain_text,
            timestamped_segments=timestamped_segments,
            include_timestamps=include_timestamps,
        )
        texts.append(_read_text(first_pass_path))

    if len(texts) != 3:
        raise RuntimeError(f"Expected 3 first-pass transcripts, got {len(texts)} for {audio_path}")

    reconcile_result = reconcile_three_transcripts(
        texts[0],
        texts[1],
        texts[2],
        write_diff_report=write_diff_report,
    )
    _write_text(final_path, reconcile_result.final_text)
    if reconcile_result.diff_report is not None:
        _write_text(final_path.with_suffix(".diff.txt"), reconcile_result.diff_report)

    return audio_path, True, None, reconcile_result


def process_audio_file_two_runs(
    *,
    audio_path: Path,
    input_dir: Path,
    first_pass_dir: Path,
    final_dir: Path,
    model_size: str,
    compute_type: str,
    language: str,
    include_timestamps: bool,
    initial_prompt: Optional[str],
    overwrite: bool,
    resume: bool,
    cpu_threads: Optional[int],
    write_diff_report: bool = True,
) -> Tuple[Path, bool, Optional[str], Optional[ReconcileResult]]:
    final_path = _compute_final_path(audio_path, input_dir, final_dir)
    if final_path.exists() and resume and not overwrite:
        logging.info("Final transcript exists; skipping due to --resume: %s", final_path)
        return audio_path, True, None, None

    first_pass_paths = [
        _compute_first_pass_path(audio_path, input_dir, first_pass_dir, run_index)
        for run_index in (1, 2)
    ]

    texts: List[str] = []
    model: Optional[WhisperModel] = None

    for run_index, first_pass_path in enumerate(first_pass_paths, start=1):
        if first_pass_path.exists() and not overwrite:
            texts.append(_read_text(first_pass_path))
            continue

        if model is None:
            model = load_model(model_size=model_size, compute_type=compute_type, cpu_threads=cpu_threads)

        random.seed(_stable_seed_for_run(audio_path, run_index))
        temperature_schedule = _temperature_schedule_for_run(run_index)
        plain_text, timestamped_segments = transcribe_with_model(
            model=model,
            audio_path=audio_path,
            language=language,
            include_timestamps=include_timestamps,
            initial_prompt=initial_prompt,
            temperature_schedule=temperature_schedule,
        )
        write_transcript(
            output_path=first_pass_path,
            plain_text=plain_text,
            timestamped_segments=timestamped_segments,
            include_timestamps=include_timestamps,
        )
        texts.append(_read_text(first_pass_path))

    if len(texts) != 2:
        raise RuntimeError(f"Expected 2 first-pass transcripts, got {len(texts)} for {audio_path}")

    reconcile_result = reconcile_two_transcripts(
        texts[0],
        texts[1],
        write_diff_report=write_diff_report,
    )
    _write_text(final_path, reconcile_result.final_text)
    if reconcile_result.diff_report is not None:
        _write_text(final_path.with_suffix(".diff.txt"), reconcile_result.diff_report)

    return audio_path, True, None, reconcile_result


def process_audio_file_one_run(
    *,
    audio_path: Path,
    input_dir: Path,
    first_pass_dir: Path,
    final_dir: Path,
    model_size: str,
    compute_type: str,
    language: str,
    include_timestamps: bool,
    initial_prompt: Optional[str],
    overwrite: bool,
    resume: bool,
    cpu_threads: Optional[int],
) -> Tuple[Path, bool, Optional[str], Optional[ReconcileResult]]:
    final_path = _compute_final_path(audio_path, input_dir, final_dir)
    if final_path.exists() and resume and not overwrite:
        logging.info("Final transcript exists; skipping due to --resume: %s", final_path)
        return audio_path, True, None, None

    first_pass_path = _compute_single_pass_path(audio_path, input_dir, first_pass_dir)
    if first_pass_path.exists() and not overwrite:
        text = _read_text(first_pass_path)
    else:
        model = load_model(model_size=model_size, compute_type=compute_type, cpu_threads=cpu_threads)
        plain_text, timestamped_segments = transcribe_with_model(
            model=model,
            audio_path=audio_path,
            language=language,
            include_timestamps=include_timestamps,
            initial_prompt=initial_prompt,
            temperature_schedule=[0.0, 0.2, 0.4],
        )
        write_transcript(
            output_path=first_pass_path,
            plain_text=plain_text,
            timestamped_segments=timestamped_segments,
            include_timestamps=include_timestamps,
        )
        text = _read_text(first_pass_path)

    _write_text(final_path, text.rstrip() + "\n")
    return audio_path, True, None, None


def _apply_power_preset(
    power: str,
    *,
    cpu_count: int,
) -> Tuple[int, int]:
    cpu_count = max(int(cpu_count), 1)
    if power == "low":
        return 1, max(1, cpu_count // 4)
    if power == "medium":
        return 1, max(1, cpu_count // 2)
    if power == "high":
        # High is still conservative on laptops: modest file-parallelism, more threads.
        return min(2, cpu_count), max(1, int(cpu_count * 0.75))
    raise ValueError(f"Unknown power preset: {power}")


def main() -> None:
    args = parse_arguments()

    repo_root = Path(__file__).resolve().parents[2]
    if args.input_dir is not None:
        input_dir = Path(args.input_dir).expanduser().resolve()
    else:
        input_dir = _default_input_dir(repo_root)

    if not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist or is not a directory: {input_dir}")

    output_dir_legacy: Optional[Path]
    if args.output_dir is not None:
        output_dir_legacy = Path(args.output_dir).expanduser().resolve()
    else:
        output_dir_legacy = None

    if args.first_pass_dir is not None:
        first_pass_dir = Path(args.first_pass_dir).expanduser().resolve()
    elif output_dir_legacy is not None:
        first_pass_dir = output_dir_legacy
    else:
        first_pass_dir = _default_output_dir(repo_root)

    if args.final_dir is not None:
        final_dir = Path(args.final_dir).expanduser().resolve()
    else:
        final_dir = _default_final_dir(repo_root)

    log_directory = first_pass_dir
    configure_logging(log_directory=log_directory)

    extensions = [ext if ext.startswith(".") else f".{ext}" for ext in args.extensions.split(",")]
    if args.queue_file is not None:
        queue_file = Path(args.queue_file).expanduser().resolve()
        audio_files = _load_queue_file(queue_file, input_dir=input_dir)
    else:
        audio_files = find_audio_files(input_dir=input_dir, extensions=extensions)
    if not audio_files:
        logging.warning("No audio files found in %s with extensions %s", input_dir, extensions)
        return

    logging.info("Found %d audio files to process.", len(audio_files))

    requested_max_workers = int(args.max_workers)
    requested_cpu_threads = args.cpu_threads
    cpu_count = os.cpu_count() or 1

    max_workers = max(requested_max_workers, 1)
    cpu_threads = requested_cpu_threads
    if args.power is not None and (requested_max_workers == 1) and (requested_cpu_threads is None):
        preset_workers, preset_threads = _apply_power_preset(args.power, cpu_count=cpu_count)
        max_workers = max(preset_workers, 1)
        cpu_threads = max(preset_threads, 1)

    set_cpu_thread_environment(cpu_threads)
    model_size = args.model_size
    compute_type = args.compute_type
    language = args.language
    include_timestamps = bool(args.include_timestamps)
    initial_prompt = args.initial_prompt
    overwrite = bool(args.overwrite)
    resume = bool(args.resume)

    runs = int(args.runs)
    if runs not in {1, 2, 3}:
        raise SystemExit("This workflow currently supports --runs 1, 2, or 3 only.")

    if args.shuffle:
        random.shuffle(audio_files)
    if args.limit is not None:
        audio_files = audio_files[: max(int(args.limit), 0)]

    if max_workers == 1:
        successful = 0
        if runs == 1:
            mode_label = "1 run"
        elif runs == 2:
            mode_label = "2 runs + reconcile"
        else:
            mode_label = "3 runs + reconcile"
        with tqdm(total=len(audio_files), desc=f"Transcribing ({mode_label})", unit="file") as progress_bar:
            for audio_path in audio_files:
                start_time = datetime.datetime.now()
                if runs == 1:
                    _, ok, error_message, reconcile_result = process_audio_file_one_run(
                        audio_path=audio_path,
                        input_dir=input_dir,
                        first_pass_dir=first_pass_dir,
                        final_dir=final_dir,
                        model_size=model_size,
                        compute_type=compute_type,
                        language=language,
                        include_timestamps=include_timestamps,
                        initial_prompt=initial_prompt,
                        overwrite=overwrite,
                        resume=resume,
                        cpu_threads=cpu_threads,
                    )
                elif runs == 2:
                    _, ok, error_message, reconcile_result = process_audio_file_two_runs(
                        audio_path=audio_path,
                        input_dir=input_dir,
                        first_pass_dir=first_pass_dir,
                        final_dir=final_dir,
                        model_size=model_size,
                        compute_type=compute_type,
                        language=language,
                        include_timestamps=include_timestamps,
                        initial_prompt=initial_prompt,
                        overwrite=overwrite,
                        resume=resume,
                        cpu_threads=cpu_threads,
                    )
                else:
                    _, ok, error_message, reconcile_result = process_audio_file_three_runs(
                        audio_path=audio_path,
                        input_dir=input_dir,
                        first_pass_dir=first_pass_dir,
                        final_dir=final_dir,
                        model_size=model_size,
                        compute_type=compute_type,
                        language=language,
                        include_timestamps=include_timestamps,
                        initial_prompt=initial_prompt,
                        overwrite=overwrite,
                        resume=resume,
                        cpu_threads=cpu_threads,
                    )
                if ok and error_message is None:
                    successful += 1
                    if reconcile_result is not None:
                        logging.info(
                            "Reconciled '%s' (disagreement %.2f%%).",
                            audio_path,
                            reconcile_result.disagreement_ratio * 100.0,
                        )
                else:
                    logging.error("Failed to process '%s': %s", audio_path, error_message)

                elapsed = datetime.datetime.now() - start_time
                logging.info("Completed '%s' in %s.", audio_path, elapsed)
                progress_bar.update(1)

        logging.info("Completed transcription. Successful: %d / %d", successful, len(audio_files))
        return

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        selected_worker = (
            process_audio_file_one_run
            if runs == 1
            else (process_audio_file_two_runs if runs == 2 else process_audio_file_three_runs)
        )
        futures = {
            executor.submit(
                selected_worker,
                audio_path=audio_path,
                input_dir=input_dir,
                first_pass_dir=first_pass_dir,
                final_dir=final_dir,
                model_size=model_size,
                compute_type=compute_type,
                language=language,
                include_timestamps=include_timestamps,
                initial_prompt=initial_prompt,
                overwrite=overwrite,
                resume=resume,
                cpu_threads=cpu_threads,
            ): audio_path
            for audio_path in audio_files
        }

        successful = 0
        if runs == 1:
            mode_label = "1 run"
        elif runs == 2:
            mode_label = "2 runs + reconcile"
        else:
            mode_label = "3 runs + reconcile"
        with tqdm(total=len(audio_files), desc=f"Transcribing (parallel, {mode_label})", unit="file") as progress_bar:
            for future in as_completed(futures):
                audio_path = futures[future]
                _, ok, error_message, reconcile_result = future.result()
                if ok:
                    successful += 1
                    if reconcile_result is not None:
                        logging.info(
                            "Reconciled '%s' (disagreement %.2f%%).",
                            audio_path,
                            reconcile_result.disagreement_ratio * 100.0,
                        )
                else:
                    if error_message is not None:
                        logging.error("Failed to transcribe '%s': %s", audio_path, error_message)
                progress_bar.update(1)

    logging.info("Completed transcription. Successful: %d / %d", successful, len(audio_files))


if __name__ == "__main__":
    main()

