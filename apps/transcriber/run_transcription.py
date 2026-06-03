#!/usr/bin/env python3

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from apps.transcriber.transcribe_lectures import (
    configure_logging,
    find_audio_files,
    process_audio_file_one_run,
    process_audio_file_two_runs,
)


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_venv_python(repo_root: Path) -> Path:
    return repo_root / ".venv" / "bin" / "python"


def ensure_venv_and_deps(repo_root: Path) -> None:
    venv_python = get_venv_python(repo_root)
    if not venv_python.exists():
        print("Creating virtual environment in .venv ...")
        subprocess.run(
            ["python3", "-m", "venv", str(repo_root / ".venv")],
            check=True,
        )

    if not venv_python.exists():
        raise SystemExit("Failed to create virtual environment (.venv).")

    print("Ensuring dependencies are installed (pip install -r requirements.txt) ...")
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-r", str(repo_root / "requirements.txt")],
        check=True,
    )

    current = Path(sys.executable).resolve()
    if current != venv_python.resolve():
        os.execv(str(venv_python), [str(venv_python), __file__])


def list_audio_files(lecture_dir: Path, extensions: Iterable[str]) -> List[Path]:
    return find_audio_files(lecture_dir, extensions)


def choose_file(files: List[Path], lecture_dir: Path) -> Path:
    while True:
        print("\nAvailable lecture recordings:")
        for idx, path in enumerate(files):
            try:
                relative_display = str(path.relative_to(lecture_dir))
            except ValueError:
                relative_display = path.name
            print(f"{idx}: {relative_display}")

        choice = input("\nEnter the index of the file to transcribe (or 'q' to quit): ").strip()
        if choice.lower() in {"q", "quit"}:
            raise SystemExit(0)

        if not choice.isdigit():
            print("Please enter a valid integer index.")
            continue

        index = int(choice)
        if not (0 <= index < len(files)):
            print("Index out of range. Try again.")
            continue

        return files[index]


def _parse_index_selection(selection: str, *, max_index: int) -> List[int]:
    raw = selection.strip()
    if not raw:
        raise ValueError("Empty selection.")
    if raw.lower() in {"q", "quit"}:
        raise SystemExit(0)

    indices: List[int] = []
    tokens = [token.strip() for token in raw.split(",") if token.strip()]
    for token in tokens:
        if "-" in token:
            start_str, end_str = [part.strip() for part in token.split("-", 1)]
            if not start_str.isdigit() or not end_str.isdigit():
                raise ValueError(f"Invalid range token: {token}")
            start = int(start_str)
            end = int(end_str)
            if start > end:
                start, end = end, start
            for idx in range(start, end + 1):
                indices.append(idx)
        else:
            if not token.isdigit():
                raise ValueError(f"Invalid index token: {token}")
            indices.append(int(token))

    unique_sorted = sorted(set(indices))
    for idx in unique_sorted:
        if idx < 0 or idx > max_index:
            raise ValueError(f"Index out of range: {idx}")
    return unique_sorted


def choose_files(files: List[Path], lecture_dir: Path) -> List[Path]:
    while True:
        print("\nAvailable lecture recordings:")
        for idx, path in enumerate(files):
            try:
                relative_display = str(path.relative_to(lecture_dir))
            except ValueError:
                relative_display = path.name
            print(f"{idx}: {relative_display}")

        choice = input(
            "\nEnter indices to transcribe (e.g. 0,2,5-7), 'u' for undone, or 'q' to quit: "
        ).strip()
        if choice.lower() == "u":
            return []
        try:
            indices = _parse_index_selection(choice, max_index=len(files) - 1)
        except ValueError as error:
            print(f"Selection error: {error}")
            continue
        return [files[i] for i in indices]


def prompt_cpu_threads() -> Optional[int]:
    while True:
        raw = input(
            "\nCPU threads to use (1-N), or press Enter for default: "
        ).strip()
        if raw == "":
            return None
        if not raw.isdigit():
            print("Please enter an integer or press Enter.")
            continue
        value = int(raw)
        if value < 1:
            print("Threads must be >= 1.")
            continue
        return value


def prompt_runs() -> int:
    while True:
        raw = input("\nNumber of passes (1=default, 2=compare+refine): ").strip()
        if raw == "":
            return 1
        if not raw.isdigit():
            print("Please enter 1 or 2 (or press Enter for 1).")
            continue
        value = int(raw)
        if value not in {1, 2}:
            print("Please enter 1 or 2.")
            continue
        return value


def compute_output_path(audio_path: Path, lecture_dir: Path, txt_output_root: Path) -> Path:
    """
    Mirror the directory structure of the audio tree under the transcripts root.
    Example:
        audio_lectures/精读/精读第五.m4a -> first_pass_transcripts/精读/精读第五.txt
        audio_lectures/TEST.m4a -> first_pass_transcripts/TEST.txt
    """
    relative = audio_path.relative_to(lecture_dir)
    return (txt_output_root / relative).with_suffix(".txt")


def summarize_transcription_status(
    audio_root: Path,
    transcripts_root: Path,
    extensions: Iterable[str],
) -> Tuple[List[Path], List[Path]]:
    """
    Return (transcribed, not_transcribed) audio file lists by comparing mirrored paths.
    """
    audio_files = find_audio_files(audio_root, extensions)
    transcribed: List[Path] = []
    not_transcribed: List[Path] = []

    for audio_path in audio_files:
        output_path = compute_output_path(audio_path, audio_root, transcripts_root)
        if output_path.exists():
            transcribed.append(audio_path)
        else:
            not_transcribed.append(audio_path)

    return transcribed, not_transcribed


def _default_lecture_dir(repo_root: Path) -> Path:
    raw_dir = repo_root / "raw_materials" / "audio_lectures"
    if raw_dir.is_dir():
        return raw_dir
    legacy_dir = repo_root / "lecture_recordings"
    return legacy_dir


def main() -> None:
    if "HF_ENDPOINT" not in os.environ:
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

    repo_root = get_repo_root()
    lecture_dir = _default_lecture_dir(repo_root)
    txt_output_dir = repo_root / "raw_materials" / "first_pass_transcripts"

    if not lecture_dir.is_dir():
        raise SystemExit(f"Lecture recordings directory does not exist: {lecture_dir}")

    txt_output_dir.mkdir(parents=True, exist_ok=True)

    ensure_venv_and_deps(repo_root)

    # Use the shared logging configuration; log file will live under audio_lectures.
    configure_logging(log_directory=lecture_dir)
    logging.info("Master transcription runner started in %s", lecture_dir)

    # Shared list of extensions; keep in sync with transcribe_lectures default and add .mp4.
    extensions = [".m4a", ".wav", ".mp3", ".flac", ".ogg", ".mp4"]

    # Status summary before doing any work.
    transcribed, not_transcribed = summarize_transcription_status(
        audio_root=lecture_dir,
        transcripts_root=txt_output_dir,
        extensions=extensions,
    )
    total = len(transcribed) + len(not_transcribed)
    print("\n=== Transcription status ===")
    print(f"Total audio files: {total}")
    print(f"Already transcribed: {len(transcribed)}")
    print(f"Not yet transcribed: {len(not_transcribed)}")
    if not_transcribed:
        print("\nFiles without transcripts (relative to audio_lectures):")
        for audio_path in not_transcribed:
            try:
                rel = audio_path.relative_to(lecture_dir)
            except ValueError:
                rel = audio_path.name
            print(f"  - {rel}")
    else:
        print("\nAll audio files currently have transcripts.")

    audio_files = find_audio_files(lecture_dir, extensions)
    if not audio_files:
        logging.warning("No audio files found in %s", lecture_dir)
        raise SystemExit(0)

    selected = choose_files(audio_files, lecture_dir)
    if not selected:
        untranscribed_path_set = {path.resolve() for path in not_transcribed}
        undone_indices: List[int] = []
        selected = []
        for index, audio_path in enumerate(audio_files):
            if audio_path.resolve() in untranscribed_path_set:
                undone_indices.append(index)
                selected.append(audio_path)

        if not selected:
            print("\nNo undone files found. Everything in the current status list is already transcribed.")
            raise SystemExit(0)

        print("\nUndone file indices (matching 'Not yet transcribed' above):")
        print(", ".join(str(index) for index in undone_indices))
        confirmation = input("Proceed with all undone files above? [y/N]: ").strip().lower()
        if confirmation not in {"y", "yes"}:
            raise SystemExit("Cancelled by user.")

    runs = prompt_runs()
    cpu_threads = prompt_cpu_threads()

    overwrite_answer = input("\nOverwrite existing outputs if present? [y/N]: ").strip().lower()
    overwrite = overwrite_answer in {"y", "yes"}

    final_dir = repo_root / "raw_materials" / "final_transcripts"

    for target in selected:
        if runs == 1:
            logging.info("Processing (1 run) %s ...", target)
            _, ok, error_message, reconcile_result = process_audio_file_one_run(
                audio_path=target,
                input_dir=lecture_dir,
                first_pass_dir=txt_output_dir,
                final_dir=final_dir,
                model_size="medium",
                compute_type="int8",
                language="zh",
                include_timestamps=True,
                initial_prompt=None,
                overwrite=overwrite,
                resume=True,
                cpu_threads=cpu_threads,
            )
        else:
            logging.info("Processing (2 runs + reconcile) %s ...", target)
            _, ok, error_message, reconcile_result = process_audio_file_two_runs(
                audio_path=target,
                input_dir=lecture_dir,
                first_pass_dir=txt_output_dir,
                final_dir=final_dir,
                model_size="medium",
                compute_type="int8",
                language="zh",
                include_timestamps=True,
                initial_prompt=None,
                overwrite=overwrite,
                resume=True,
                cpu_threads=cpu_threads,
            )
        if not ok:
            raise SystemExit(f"Failed processing {target}: {error_message}")
        if reconcile_result is not None:
            logging.info(
                "Reconciled '%s' (disagreement %.2f%%).",
                target.name,
                reconcile_result.disagreement_ratio * 100.0,
            )

    logging.info("Done transcribing %d files.", len(selected))


if __name__ == "__main__":
    main()

