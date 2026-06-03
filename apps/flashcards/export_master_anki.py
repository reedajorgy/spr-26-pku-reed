#!/usr/bin/env python3
"""
Build the master finals Anki package: all courses, chapters, aspects, and locales.

Writes outputs/finals-master.apkg by default (683 notes across Vocab, Grammar,
and Word_Differences subdecks under Kouyu and Jingdu).

Example:
  PYTHONPATH=. python apps/flashcards/export_master_anki.py
  PYTHONPATH=. python apps/flashcards/export_master_anki.py --output outputs/my-deck.apkg
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

from apps.flashcards.anki_master import build_master_finals_package, summarize_master_package
from apps.flashcards.locale_manifest import master_deck_name
from apps.flashcards.paths import FINALS_DIR

DEFAULT_OUTPUT = REPO_ROOT / "outputs" / "finals-master.apkg"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export all flashcard aspects to one nested Anki deck.",
    )
    parser.add_argument(
        "--deck-name",
        default=None,
        help=f"Root deck name (default: {master_deck_name()!r} from manifest)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output .apkg path",
    )
    parser.add_argument("--finals-dir", type=Path, default=FINALS_DIR)
    args = parser.parse_args()

    root_name = args.deck_name or master_deck_name()
    output_path = args.output if args.output.is_absolute() else REPO_ROOT / args.output

    package = build_master_finals_package(root_name, finals_dir=args.finals_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    package.write_to_file(str(output_path))

    note_count, card_count, subdeck_counts = summarize_master_package(finals_dir=args.finals_dir)
    aspects = sorted({name.split("::")[-1] for name in subdeck_counts})
    print(f"Wrote {output_path}")
    print(f"  Root deck: {root_name}")
    print(f"  Aspects: {', '.join(aspects)}")
    print(f"  Subdecks: {len(subdeck_counts)}")
    print(f"  Notes: {note_count}, cards: {card_count}")


if __name__ == "__main__":
    main()
