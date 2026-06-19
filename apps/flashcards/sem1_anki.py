"""Build nested Anki packages from PKU Sem 1 category CSV files."""

from __future__ import annotations

import csv
import html
import re
from collections import Counter
from pathlib import Path

import genanki

from apps.flashcards.anki_build import build_vocab_model, row_to_vocab_fields, stable_id
from apps.flashcards.paths import FINALS_DIR
from apps.flashcards.sem1_merge import CATEGORY_OUTPUT_FILES

SEM1_ROOT_DECK_NAME = "PKU Sem 1"

SEM1_CATEGORY_LABELS: dict[str, str] = {
    "chengyu": "成语",
    "proper-nouns": "专用名词",
    "vocab": "生词",
    "literature-chengyu": "文学课::成语",
    "literature-vocab": "文学课::生词",
    "literature-proper-nouns": "文学课::专有名词",
}

_CSV_TO_ANKI: dict[str, str] = {
    "Chapter": "Chapter",
    "hanzi": "Hanzi",
    "pinyin": "Pinyin",
    "mandarin_意义": "MandarinDef",
    "英文意义": "English",
    "词性": "POS",
    "搭配": "Collocations",
    "色彩": "Color",
    "example_sentence": "ExampleCN",
    "example_sentence_en": "ExampleEN",
    "usage_note": "UsageNote",
    "common_errors": "CommonErrors",
    "related_words": "RelatedWords",
}


def sem1_chapter_segment(chapter: str) -> str:
    return chapter.split("；")[0].strip()


def sem1_chapter_slug(chapter: str) -> str:
    segment = sem1_chapter_segment(chapter)
    slug = segment.replace("/", "_").replace(" ", "_")
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "Uncategorized"


def sem1_subdeck_name(root_name: str, category_key: str, chapter: str) -> str:
    category_label = SEM1_CATEGORY_LABELS[category_key]
    chapter_slug = sem1_chapter_slug(chapter)
    return f"{root_name}::{category_label}::{chapter_slug}"


def load_sem1_category_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


_TAG_RE = re.compile(r"<[^>]+>")


def _sanitize_field(value: str) -> str:
    cleaned = _TAG_RE.sub("", value or "").strip()
    return html.escape(cleaned, quote=False)


def csv_row_to_anki_row(csv_row: dict[str, str]) -> dict[str, str]:
    return {
        anki_field: _sanitize_field(csv_row.get(csv_column, ""))
        for csv_column, anki_field in _CSV_TO_ANKI.items()
    }


def load_all_sem1_anki_rows(
    finals_dir: Path | None = None,
) -> list[tuple[str, dict[str, str]]]:
    base_dir = finals_dir or FINALS_DIR
    loaded: list[tuple[str, dict[str, str]]] = []
    for category_key, filename in CATEGORY_OUTPUT_FILES.items():
        csv_path = base_dir / filename
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing Sem 1 CSV: {csv_path}")
        for csv_row in load_sem1_category_rows(csv_path):
            loaded.append((category_key, csv_row_to_anki_row(csv_row)))
    return loaded


def build_sem1_package(
    root_deck_name: str = SEM1_ROOT_DECK_NAME,
    *,
    finals_dir: Path | None = None,
) -> genanki.Package:
    model = build_vocab_model("en")
    deck_registry: dict[str, genanki.Deck] = {}

    for category_key, row in load_all_sem1_anki_rows(finals_dir=finals_dir):
        chapter = row.get("Chapter", "").strip()
        if not chapter:
            continue
        subdeck_name = sem1_subdeck_name(root_deck_name, category_key, chapter)
        if subdeck_name not in deck_registry:
            deck_id = stable_id(f"spr-26-pku.sem1.deck.{subdeck_name}")
            deck_registry[subdeck_name] = genanki.Deck(deck_id, subdeck_name)

        chapter_slug = sem1_chapter_slug(chapter)
        tags = ["sem1", category_key.replace("-", "_"), chapter_slug.lower()]
        note = genanki.Note(
            model=model,
            fields=row_to_vocab_fields(row),
            tags=tags,
        )
        deck_registry[subdeck_name].add_note(note)

    all_decks = sorted(deck_registry.values(), key=lambda deck: deck.name)
    if not all_decks:
        raise ValueError("No Sem 1 notes generated for Anki package")

    package = genanki.Package(all_decks[0])
    package.decks = all_decks
    package.models = [model]
    return package


def summarize_sem1_package(
    root_deck_name: str = SEM1_ROOT_DECK_NAME,
    *,
    finals_dir: Path | None = None,
) -> tuple[int, int, Counter[str]]:
    note_count = 0
    card_count = 0
    subdeck_counts: Counter[str] = Counter()
    for category_key, row in load_all_sem1_anki_rows(finals_dir=finals_dir):
        chapter = row.get("Chapter", "").strip()
        if not chapter:
            continue
        subdeck_name = sem1_subdeck_name(root_deck_name, category_key, chapter)
        subdeck_counts[subdeck_name] += 1
        note_count += 1
        card_count += 2
    return note_count, card_count, subdeck_counts
