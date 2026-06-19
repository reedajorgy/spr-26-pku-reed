#!/usr/bin/env python3
"""
Build the combined elective-course Anki package: Baokan + Yingshi vocab.

Writes outputs/xuanxiu-ke.apkg by default with the same multilocale vocab
card templates as Kouyu/Jingdu finals decks.

Example:
  PYTHONPATH=. python apps/flashcards/export_xuanxiu_anki.py
  PYTHONPATH=. python apps/flashcards/export_xuanxiu_anki.py --output outputs/my-xuanxiu.apkg
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

from apps.flashcards.anki_master import (
    XUANXIU_ROOT_DECK_NAME,
    build_xuanxiu_package,
    summarize_xuanxiu_package,
)
from apps.flashcards.paths import FINALS_DIR

DEFAULT_OUTPUT = REPO_ROOT / "outputs" / "xuanxiu-ke.apkg"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Baokan + Yingshi vocab to one nested Anki deck.",
    )
    parser.add_argument(
        "--deck-name",
        default=None,
        help=f"Root deck name (default: {XUANXIU_ROOT_DECK_NAME!r})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output .apkg path",
    )
    parser.add_argument("--finals-dir", type=Path, default=FINALS_DIR)
    args = parser.parse_args()

    root_name = args.deck_name or XUANXIU_ROOT_DECK_NAME
    output_path = args.output if args.output.is_absolute() else REPO_ROOT / args.output

    package = build_xuanxiu_package(root_name, finals_dir=args.finals_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    package.write_to_file(str(output_path))

    note_count, card_count, subdeck_counts = summarize_xuanxiu_package(
        root_name,
        finals_dir=args.finals_dir,
    )
    print(f"Wrote {output_path}")
    print(f"  Root deck: {root_name}")
    print(f"  Subdecks: {len(subdeck_counts)}")
    print(f"  Notes: {note_count}, cards: {card_count}")


if __name__ == "__main__":
    main()
