from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FINALS_DIR = REPO_ROOT / "finals-flashcards-csvs"
LOCALES_DIR = FINALS_DIR / "locales"
MANIFEST_PATH = LOCALES_DIR / "manifest.json"

SUPPORTED_OVERLAY_LOCALES = ("ru", "ko", "ja", "es", "vi", "hi", "fr")


def master_csv_path(deck_name: str) -> Path:
    return FINALS_DIR / f"{deck_name}.csv"


def locale_csv_path(locale: str, deck_name: str) -> Path:
    return LOCALES_DIR / locale / f"{deck_name}.csv"


def resolve_repo_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return REPO_ROOT / path
