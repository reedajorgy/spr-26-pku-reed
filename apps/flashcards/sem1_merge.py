"""Merge enriched Sem 1 rows and assign export categories."""

from __future__ import annotations

from dataclasses import replace

from apps.flashcards.sem1_enrich import EnrichedSem1Row

CATEGORY_PRIORITY: tuple[str, ...] = (
    "literature-chengyu",
    "chengyu",
    "literature-proper-nouns",
    "proper-nouns",
    "literature-vocab",
    "vocab",
)

CATEGORY_OUTPUT_FILES: dict[str, str] = {
    "chengyu": "pku-sem1-chengyu.csv",
    "proper-nouns": "pku-sem1-proper-nouns.csv",
    "vocab": "pku-sem1-vocab.csv",
    "literature-chengyu": "pku-sem1-literature-chengyu.csv",
    "literature-vocab": "pku-sem1-literature-vocab.csv",
    "literature-proper-nouns": "pku-sem1-literature-proper-nouns.csv",
}

MASTER_OUTPUT_FILE = "pku-sem1-master.csv"


def _priority_for_category(category: str) -> int:
    try:
        return CATEGORY_PRIORITY.index(category)
    except ValueError:
        return len(CATEGORY_PRIORITY)


def resolve_export_category(categories: set[str]) -> str:
    if not categories:
        return "vocab"
    return min(categories, key=_priority_for_category)


def _split_field(value: str) -> list[str]:
    if not value:
        return []
    parts: list[str] = []
    for chunk in value.replace(";", "；").split("；"):
        cleaned = chunk.strip()
        if cleaned and cleaned not in parts:
            parts.append(cleaned)
    return parts


def _join_field(parts: list[str]) -> str:
    return "；".join(parts)


def _pick_pinyin(rows: list[EnrichedSem1Row]) -> str:
    candidates = [row.pinyin for row in rows if row.pinyin.strip()]
    if not candidates:
        return ""
    return max(candidates, key=len)


def _merge_rows(rows: list[EnrichedSem1Row]) -> EnrichedSem1Row:
    base = rows[0]
    chapters = _join_field(_split_field("; ".join(row.chapter for row in rows)))
    categories = set().union(*(row.source_categories for row in rows))
    export_category = resolve_export_category(categories)

    english_parts: list[str] = []
    mandarin_parts: list[str] = []
    collocation_parts: list[str] = []
    related_parts: list[str] = []
    chinese_examples: list[str] = []
    english_examples: list[str] = []
    usage_notes: list[str] = []

    for row in rows:
        english_parts.extend(_split_field(row.english_meaning))
        mandarin_parts.extend(_split_field(row.mandarin_meaning))
        collocation_parts.extend(_split_field(row.collocations))
        related_parts.extend(_split_field(row.related_words))
        if row.example_sentence and row.example_sentence not in chinese_examples:
            chinese_examples.append(row.example_sentence)
        if row.example_sentence_en and row.example_sentence_en not in english_examples:
            english_examples.append(row.example_sentence_en)
        if row.usage_note and row.usage_note not in usage_notes:
            usage_notes.append(row.usage_note)

    best_row = max(rows, key=lambda row: len(row.english_meaning))
    return replace(
        base,
        pinyin=_pick_pinyin(rows),
        mandarin_meaning=_join_field(mandarin_parts),
        english_meaning=_join_field(english_parts),
        pos=best_row.pos,
        collocations=_join_field(collocation_parts),
        color=best_row.color,
        example_sentence=chinese_examples[0] if chinese_examples else "",
        example_sentence_en=english_examples[0] if english_examples else "",
        usage_note=" ".join(usage_notes[:2]),
        related_words=_join_field(related_parts),
        chapter=chapters,
        source_category=export_category,
        source_categories=categories,
    )


def merge_enriched_rows(rows: list[EnrichedSem1Row]) -> list[EnrichedSem1Row]:
    grouped: dict[str, list[EnrichedSem1Row]] = {}
    for row in rows:
        grouped.setdefault(row.hanzi, []).append(row)

    merged: list[EnrichedSem1Row] = []
    for hanzi in sorted(grouped):
        merged.append(_merge_rows(grouped[hanzi]))
    return merged


def group_rows_by_export_category(
    rows: list[EnrichedSem1Row],
) -> dict[str, list[EnrichedSem1Row]]:
    grouped: dict[str, list[EnrichedSem1Row]] = {key: [] for key in CATEGORY_OUTPUT_FILES}
    for row in rows:
        category = row.source_category
        if category not in grouped:
            category = resolve_export_category(row.source_categories)
        grouped[category].append(row)
    return grouped
