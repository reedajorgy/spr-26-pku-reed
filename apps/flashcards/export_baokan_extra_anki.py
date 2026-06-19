#!/usr/bin/env python3
"""
Normalize outputs/baokan-extra.csv and export it as an Anki deck.

Example:
  PYTHONPATH=. python apps/flashcards/export_baokan_extra_anki.py
  PYTHONPATH=. python apps/flashcards/export_baokan_extra_anki.py --csv-only
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

from apps.flashcards.baokan_extra import (
    DEFAULT_CSV_PATH,
    DEFAULT_DECK_NAME,
    build_baokan_extra_package,
    load_baokan_extra_rows,
    normalize_baokan_extra_csv,
)

DEFAULT_OUTPUT = REPO_ROOT / "outputs" / "baokan-extra.apkg"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize Baokan extra notes CSV and export an Anki deck.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help="Input notes file (CSV or legacy Python export script)",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help="Normalized CSV output path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output .apkg path",
    )
    parser.add_argument(
        "--deck-name",
        default=DEFAULT_DECK_NAME,
        help=f"Anki deck name (default: {DEFAULT_DECK_NAME!r})",
    )
    parser.add_argument(
        "--csv-only",
        action="store_true",
        help="Only normalize the CSV; do not write an .apkg file",
    )
    args = parser.parse_args()

    source_path = args.source if args.source.is_absolute() else REPO_ROOT / args.source
    csv_output_path = (
        args.csv_output if args.csv_output.is_absolute() else REPO_ROOT / args.csv_output
    )
    normalized_path, rows = normalize_baokan_extra_csv(
        source_path=source_path,
        output_path=csv_output_path,
    )
    print(f"Wrote normalized CSV: {normalized_path}")
    print(f"  Cards: {len(rows)}")

    if args.csv_only:
        return

    output_path = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    package = build_baokan_extra_package(
        args.deck_name,
        rows=rows,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    package.write_to_file(str(output_path))
    print(f"Wrote {output_path}")
    print(f"  Deck: {args.deck_name}")
    print(f"  Notes: {len(rows)}")


if __name__ == "__main__":
    main()
