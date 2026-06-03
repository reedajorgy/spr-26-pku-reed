from __future__ import annotations

from collections import defaultdict
from typing import Any

from apps.flashcards.locale_manifest import (
    aspect_for_deck,
    get_course_specs,
    master_deck_name,
)
from apps.flashcards.merge import merge_deck_rows_multilocale


def build_hierarchy_summary(*, finals_dir=None) -> dict[str, Any]:
    """Aggregate note counts by course, chapter, and aspect for web UI / validation."""
    root_name = master_deck_name()
    tree: dict[str, Any] = {
        "root": root_name,
        "courses": {},
        "total_notes": 0,
    }

    for course_key, course_spec in get_course_specs().items():
        course_node: dict[str, Any] = {
            "key": course_key,
            "label": course_spec.label,
            "label_zh": course_spec.label_zh,
            "chapters": {},
            "note_count": 0,
        }
        chapter_notes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for deck_key in course_spec.deck_keys:
            aspect = aspect_for_deck(deck_key)
            rows = merge_deck_rows_multilocale(deck_key, finals_dir=finals_dir)
            for row in rows:
                chapter = row["master"].get("Chapter", "")
                if not chapter:
                    continue
                chapter_notes[chapter][aspect] += 1
                course_node["note_count"] += 1
                tree["total_notes"] += 1

        for chapter_label in sorted(
            chapter_notes.keys(),
            key=lambda label: int("".join(filter(str.isdigit, label)) or "0"),
        ):
            aspects = chapter_notes[chapter_label]
            course_node["chapters"][chapter_label] = {
                "aspects": dict(aspects),
                "note_count": sum(aspects.values()),
                "subdecks": {
                    aspect: f"{root_name}::{course_spec.label}::Chapter_{''.join(filter(str.isdigit, chapter_label))}::{aspect}"
                    for aspect in aspects
                },
            }

        tree["courses"][course_key] = course_node

    return tree


def deck_keys_for_filters(
    course: str | None = None,
    aspect: str | None = None,
) -> list[str] | None:
    """Resolve course/aspect filters to deck keys, or None for all decks."""
    if not course and not aspect:
        return None

    from apps.flashcards.locale_manifest import get_aspect_map

    aspect_map = get_aspect_map()
    deck_keys: list[str] = []

    for course_key, course_spec in get_course_specs().items():
        if course and course_key != course:
            continue
        for deck_key in course_spec.deck_keys:
            if aspect and aspect_map.get(deck_key) != aspect:
                continue
            deck_keys.append(deck_key)

    return deck_keys
