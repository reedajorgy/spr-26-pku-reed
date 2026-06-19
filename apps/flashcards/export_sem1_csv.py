#!/usr/bin/env python3
"""Export PKU Sem 1 source list into category Anki-ready CSV files."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.flashcards.cedict_lookup import CedictLookup, ensure_cedict, fetch_cedict
from apps.flashcards.paths import FINALS_DIR
from apps.flashcards.sem1_enrich import enrich_source_rows
from apps.flashcards.sem1_merge import (
    CATEGORY_OUTPUT_FILES,
    MASTER_OUTPUT_FILE,
    group_rows_by_export_category,
    merge_enriched_rows,
)
from apps.flashcards.sem1_source import parse_sem1_source

CSV_HEADER = [
    "Chapter",
    "hanzi",
    "pinyin",
    "mandarin_意义",
    "英文意义",
    "词性",
    "搭配",
    "色彩",
    "example_sentence",
    "example_sentence_en",
    "usage_note",
    "common_errors",
    "related_words",
]

MASTER_HEADER = ["category", *CSV_HEADER]

DEFAULT_SOURCE = FINALS_DIR / "Pku Sem 1.txt"


def _row_to_csv_dict(row, *, category: str | None = None) -> dict[str, str]:
    values = {
        "Chapter": row.chapter,
        "hanzi": row.hanzi,
        "pinyin": row.pinyin,
        "mandarin_意义": row.mandarin_meaning,
        "英文意义": row.english_meaning,
        "词性": row.pos,
        "搭配": row.collocations,
        "色彩": row.color,
        "example_sentence": row.example_sentence,
        "example_sentence_en": row.example_sentence_en,
        "usage_note": row.usage_note,
        "common_errors": row.common_errors,
        "related_words": row.related_words,
    }
    if category is not None:
        values = {"category": category, **values}
    return values


def _write_csv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def build_sem1_csv_rows(
    source_path: Path,
    *,
    cedict: CedictLookup | None = None,
) -> tuple[list, dict[str, list], dict[str, int]]:
    source_rows = parse_sem1_source(source_path)
    enriched_rows = enrich_source_rows(source_rows, cedict=cedict)
    merged_rows = merge_enriched_rows(enriched_rows)
    grouped = group_rows_by_export_category(merged_rows)

    stats = {
        "source_rows": len(source_rows),
        "merged_rows": len(merged_rows),
        "empty_source_glosses": sum(1 for row in source_rows if not row.raw_gloss.strip()),
        "empty_english_after_enrich": sum(1 for row in merged_rows if not row.english_meaning.strip()),
        "empty_mandarin_after_enrich": sum(
            1 for row in merged_rows if not row.mandarin_meaning.strip()
        ),
    }
    per_file_counts = {name: len(rows) for name, rows in grouped.items()}
    return merged_rows, grouped, {**stats, **per_file_counts}


def export_sem1_csvs(
    source_path: Path,
    out_dir: Path,
    *,
    cedict: CedictLookup | None = None,
) -> dict[str, int]:
    merged_rows, grouped, stats = build_sem1_csv_rows(source_path, cedict=cedict)

    for category, filename in CATEGORY_OUTPUT_FILES.items():
        csv_rows = [
            _row_to_csv_dict(row)
            for row in sorted(grouped[category], key=lambda item: (item.chapter, item.hanzi))
        ]
        _write_csv(out_dir / filename, CSV_HEADER, csv_rows)

    master_rows = [
        _row_to_csv_dict(row, category=row.source_category)
        for row in sorted(merged_rows, key=lambda item: (item.source_category, item.hanzi))
    ]
    _write_csv(out_dir / MASTER_OUTPUT_FILE, MASTER_HEADER, master_rows)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Export PKU Sem 1 category CSV files.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out-dir", type=Path, default=FINALS_DIR)
    parser.add_argument(
        "--fetch-cedict",
        action="store_true",
        help="Download CC-CEDICT before export (also auto-fetches if missing).",
    )
    parser.add_argument(
        "--no-cedict",
        action="store_true",
        help="Skip CC-CEDICT gap-filling.",
    )
    args = parser.parse_args()

    source_path = args.source if args.source.is_absolute() else REPO_ROOT / args.source
    out_dir = args.out_dir if args.out_dir.is_absolute() else REPO_ROOT / args.out_dir

    cedict: CedictLookup | None = None
    if not args.no_cedict:
        if args.fetch_cedict:
            fetch_cedict()
        cedict = ensure_cedict()

    stats = export_sem1_csvs(source_path, out_dir, cedict=cedict)

    print(f"Source: {source_path}")
    print(f"Output dir: {out_dir}")
    print(f"  Source rows: {stats['source_rows']}")
    print(f"  Merged headwords: {stats['merged_rows']}")
    print(f"  Empty source glosses: {stats['empty_source_glosses']}")
    print(f"  Empty English after enrich: {stats['empty_english_after_enrich']}")
    print(f"  Empty Mandarin after enrich: {stats['empty_mandarin_after_enrich']}")
    for category, filename in CATEGORY_OUTPUT_FILES.items():
        print(f"  {filename}: {stats[category]}")
    print(f"  {MASTER_OUTPUT_FILE}: {stats['merged_rows']}")


if __name__ == "__main__":
    main()
