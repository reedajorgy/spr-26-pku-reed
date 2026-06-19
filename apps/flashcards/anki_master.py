from __future__ import annotations

from collections import Counter
from pathlib import Path

import genanki

from apps.flashcards.anki_build import (
    chapter_slug_from_label,
    deck_subcourse_label,
    expand_collocations,
    parse_chapter_number,
    stable_id,
)
from apps.flashcards.card_templates import (
    build_multilocale_differences_model,
    build_multilocale_jingdu_grammar_model,
    build_multilocale_kouyu_grammar_model,
    build_multilocale_vocab_model,
    multilocale_field_names,
)
from apps.flashcards.locale_manifest import (
    anki_master_course_keys,
    aspect_for_deck,
    course_for_deck,
    course_label_for_deck,
    get_course_specs,
    get_deck_specs,
    master_deck_name,
)
from apps.flashcards.merge import (
    merge_grammar_for_anki_multilocale,
    merge_vocab_for_anki_multilocale,
)
from apps.flashcards.paths import FINALS_DIR


def aspect_subdeck_name(
    root_name: str,
    course_label: str,
    chapter_label: str,
    aspect: str,
    *,
    deck_key: str | None = None,
) -> str:
    chapter_slug = chapter_slug_from_label(chapter_label)
    subcourse_label = deck_subcourse_label(deck_key) if deck_key else None
    if subcourse_label:
        return f"{root_name}::{course_label}::{subcourse_label}::{chapter_slug}::{aspect}"
    return f"{root_name}::{course_label}::{chapter_slug}::{aspect}"


def _row_values_in_order(row: dict[str, str], field_names: list[str]) -> list[str]:
    return [row.get(name, "") for name in field_names]


def _aspect_tag(aspect: str) -> str:
    mapping = {
        "Vocab": "vocab",
        "Grammar": "grammar",
        "Word_Differences": "differences",
    }
    return mapping.get(aspect, aspect.lower())


def _deck_model_and_field_names(deck_key: str) -> tuple[genanki.Model, list[str]]:
    spec = get_deck_specs()[deck_key]
    if spec.anki_vocab:
        model = build_multilocale_vocab_model()
        field_names = [
            "Chapter",
            "Hanzi",
            "Pinyin",
            "MandarinDef",
            "POS",
            "Collocations",
            "Color",
            "ExampleCN",
            "CommonErrors",
            "RelatedWords",
            *multilocale_field_names(spec.overlay_fields),
        ]
        return model, field_names
    if deck_key == "jingdu-qimo-grammar":
        return build_multilocale_jingdu_grammar_model(), [
            "Chapter",
            "GrammarPoint",
            "Example1CN",
            "Example2CN",
            "Example3CN",
            *multilocale_field_names(spec.overlay_fields),
        ]
    if deck_key == "kouyu-qimo-grammar":
        return build_multilocale_kouyu_grammar_model(), [
            "Chapter",
            "Pattern",
            "Example1",
            "Example2",
            "Example3",
            "Example4",
            "Example5",
            *multilocale_field_names(spec.overlay_fields),
        ]
    return build_multilocale_differences_model(), [
        "Chapter",
        "WordPair",
        "Word",
        "Example1CN",
        "Example2CN",
        *multilocale_field_names(spec.overlay_fields),
    ]


def _prepare_vocab_row(row: dict[str, str]) -> dict[str, str]:
    prepared = dict(row)
    prepared["Collocations"] = expand_collocations(row["Collocations"], row["Hanzi"])
    return prepared


XUANXIU_ROOT_DECK_NAME = "选修课 (Xuanxiu Ke)"


def build_anki_package(
    root_deck_name: str,
    *,
    course_keys: list[str] | None = None,
    finals_dir: Path | None = None,
) -> genanki.Package:
    base_dir = finals_dir or FINALS_DIR
    course_specs = get_course_specs()
    if course_keys is not None:
        selected_courses = [
            course_specs[course_key]
            for course_key in course_keys
            if course_key in course_specs
        ]
        if not selected_courses:
            raise ValueError(f"No matching courses for keys: {course_keys}")
    else:
        selected_courses = list(course_specs.values())

    deck_registry: dict[str, genanki.Deck] = {}
    models_by_id: dict[int, genanki.Model] = {}
    model_cache: dict[str, genanki.Model] = {}
    field_names_cache: dict[str, list[str]] = {}

    for course_spec in selected_courses:
        for deck_key in course_spec.deck_keys:
            if deck_key not in model_cache:
                model, field_names = _deck_model_and_field_names(deck_key)
                model_cache[deck_key] = model
                field_names_cache[deck_key] = field_names
                models_by_id[model.model_id] = model

            spec = get_deck_specs()[deck_key]
            model = model_cache[deck_key]
            field_names = field_names_cache[deck_key]
            course_label = course_label_for_deck(deck_key)
            aspect = aspect_for_deck(deck_key)
            tag_course = course_for_deck(deck_key)
            tag_aspect = _aspect_tag(aspect)

            if spec.anki_vocab:
                rows = merge_vocab_for_anki_multilocale(deck_key, finals_dir=base_dir)
                rows = [_prepare_vocab_row(row) for row in rows]
            else:
                rows = merge_grammar_for_anki_multilocale(deck_key, finals_dir=base_dir)

            for row in rows:
                chapter = row.get("Chapter", "")
                if not chapter:
                    continue
                subdeck = aspect_subdeck_name(
                    root_deck_name,
                    course_label,
                    chapter,
                    aspect,
                    deck_key=deck_key,
                )
                if subdeck not in deck_registry:
                    deck_registry[subdeck] = genanki.Deck(
                        stable_id(f"spr-26-pku.master.{subdeck}"),
                        subdeck,
                    )
                chapter_number = parse_chapter_number(chapter)
                tags = [tag_course, tag_aspect, "qimo", f"ch{chapter_number}"]
                note = genanki.Note(
                    model=model,
                    fields=_row_values_in_order(row, field_names),
                    tags=tags,
                )
                deck_registry[subdeck].add_note(note)

    all_decks = sorted(deck_registry.values(), key=lambda deck: deck.name)
    if not all_decks:
        raise ValueError("No notes generated for master finals package")

    package = genanki.Package(all_decks[0])
    package.decks = all_decks
    package.models = list(models_by_id.values())
    return package


def build_master_finals_package(
    root_deck_name: str | None = None,
    *,
    finals_dir: Path | None = None,
) -> genanki.Package:
    return build_anki_package(
        root_deck_name or master_deck_name(),
        course_keys=anki_master_course_keys(),
        finals_dir=finals_dir,
    )


def build_xuanxiu_package(
    root_deck_name: str | None = None,
    *,
    finals_dir: Path | None = None,
) -> genanki.Package:
    return build_anki_package(
        root_deck_name or XUANXIU_ROOT_DECK_NAME,
        course_keys=["xuanxiu"],
        finals_dir=finals_dir,
    )


def summarize_anki_package(
    root_deck_name: str,
    *,
    course_keys: list[str] | None = None,
    finals_dir: Path | None = None,
) -> tuple[int, int, Counter[str]]:
    note_count = 0
    card_count = 0
    subdeck_counts: Counter[str] = Counter()
    base_dir = finals_dir or FINALS_DIR
    course_specs = get_course_specs()
    if course_keys is not None:
        selected_courses = [
            course_specs[course_key]
            for course_key in course_keys
            if course_key in course_specs
        ]
    else:
        selected_courses = list(course_specs.values())

    for course_spec in selected_courses:
        for deck_key in course_spec.deck_keys:
            spec = get_deck_specs()[deck_key]
            course_label = course_label_for_deck(deck_key)
            aspect = aspect_for_deck(deck_key)
            if spec.anki_vocab:
                rows = merge_vocab_for_anki_multilocale(deck_key, finals_dir=base_dir)
                cards_per = 2
            else:
                rows = merge_grammar_for_anki_multilocale(deck_key, finals_dir=base_dir)
                cards_per = 1
            for row in rows:
                chapter = row.get("Chapter", "")
                if not chapter:
                    continue
                subdeck = aspect_subdeck_name(
                    root_deck_name,
                    course_label,
                    chapter,
                    aspect,
                    deck_key=deck_key,
                )
                subdeck_counts[subdeck] += 1
                note_count += 1
                card_count += cards_per
    return note_count, card_count, subdeck_counts


def summarize_master_package(
    *,
    finals_dir: Path | None = None,
) -> tuple[int, int, Counter[str]]:
    return summarize_anki_package(
        master_deck_name(),
        course_keys=anki_master_course_keys(),
        finals_dir=finals_dir,
    )


def summarize_xuanxiu_package(
    root_deck_name: str | None = None,
    *,
    finals_dir: Path | None = None,
) -> tuple[int, int, Counter[str]]:
    return summarize_anki_package(
        root_deck_name or XUANXIU_ROOT_DECK_NAME,
        course_keys=["xuanxiu"],
        finals_dir=finals_dir,
    )
