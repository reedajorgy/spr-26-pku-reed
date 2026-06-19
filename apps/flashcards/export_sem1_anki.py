#!/usr/bin/env python3
"""
Export PKU Sem 1 category CSVs to one nested Anki deck (.apkg).

Deck hierarchy:
  PKU Sem 1::成语::September_2025_成语
  PKU Sem 1::生词::October_2025_生词
  PKU Sem 1::文学课::成语::...

Example:
  PYTHONPATH=. python apps/flashcards/export_sem1_anki.py
  PYTHONPATH=. python apps/flashcards/export_sem1_anki.py --output outputs/pku-sem1.apkg
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    import genanki
except ImportError:
    print("Missing dependency: pip install genanki", file=sys.stderr)
    sys.exit(1)

from apps.flashcards.paths import FINALS_DIR
from apps.flashcards.sem1_anki import (
    SEM1_ROOT_DECK_NAME,
    build_sem1_package,
    summarize_sem1_package,
)

DEFAULT_OUTPUT = REPO_ROOT / "outputs" / "pku-sem1.apkg"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export PKU Sem 1 vocab CSVs to a nested Anki deck.",
    )
    parser.add_argument(
        "--deck-name",
        default=None,
        help=f"Root deck name (default: {SEM1_ROOT_DECK_NAME!r})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output .apkg path",
    )
    parser.add_argument("--finals-dir", type=Path, default=FINALS_DIR)
    args = parser.parse_args()

    root_name = args.deck_name or SEM1_ROOT_DECK_NAME
    output_path = args.output if args.output.is_absolute() else REPO_ROOT / args.output

    package = build_sem1_package(root_name, finals_dir=args.finals_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    package.write_to_file(str(output_path))

    note_count, card_count, subdeck_counts = summarize_sem1_package(
        root_name,
        finals_dir=args.finals_dir,
    )
    print(f"Wrote {output_path}")
    print(f"  Root deck: {root_name}")
    print(f"  Subdecks: {len(subdeck_counts)}")
    print(f"  Notes: {note_count}, cards: {card_count}")


if __name__ == "__main__":
    main()
