#!/usr/bin/env python3

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import List

from apps.transcriber.transcribe_lectures import configure_logging, transcribe_audio_file


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


def list_m4a_files(lecture_dir: Path) -> List[Path]:
    files = sorted(lecture_dir.glob("*.m4a"))
    return files


def choose_file(files: List[Path]) -> Path:
    while True:
        print("\nAvailable lecture recordings:")
        for idx, path in enumerate(files):
            print(f"{idx}: {path.name}")

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

    configure_logging(log_directory=lecture_dir)
    logging.info("Master transcription runner started in %s", lecture_dir)

    files = list_m4a_files(lecture_dir)
    if not files:
        logging.warning("No .m4a files found in %s", lecture_dir)
        raise SystemExit(0)

    target = choose_file(files)
    output_path = txt_output_dir / target.with_suffix(".txt").name

    if output_path.exists():
        answer = input(f"Transcript {output_path} already exists. Overwrite? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            logging.info("Leaving existing transcript unchanged for '%s'.", output_path)
            return
    logging.info("Transcribing %s -> %s ...", target.name, output_path.name)
    transcribe_audio_file(
        audio_path=target,
        output_path=output_path,
        model_size="medium",
        compute_type="int8",
        language="zh",
        include_timestamps=True,
        initial_prompt=None,
    )
    logging.info("Done transcribing %s.", target.name)


if __name__ == "__main__":
    main()

