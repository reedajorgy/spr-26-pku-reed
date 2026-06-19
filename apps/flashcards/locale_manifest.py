from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from apps.flashcards.paths import MANIFEST_PATH, SUPPORTED_OVERLAY_LOCALES


@dataclass(frozen=True)
class DeckSpec:
    name: str
    master_file: str
    join_keys: list[str]
    master_fields: dict[str, str]
    overlay_fields: list[str]
    anki_vocab: bool

    @property
    def overlay_header(self) -> list[str]:
        return [*self.join_keys, *self.overlay_fields]


@dataclass(frozen=True)
class CourseSpec:
    key: str
    label: str
    label_zh: str
    deck_keys: list[str]


def load_manifest(manifest_path: Path | None = None) -> dict[str, Any]:
    path = manifest_path or MANIFEST_PATH
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def get_deck_specs(manifest: dict[str, Any] | None = None) -> dict[str, DeckSpec]:
    data = manifest or load_manifest()
    specs: dict[str, DeckSpec] = {}
    for deck_name, deck_config in data["decks"].items():
        specs[deck_name] = DeckSpec(
            name=deck_name,
            master_file=deck_config["master_file"],
            join_keys=list(deck_config["join_keys"]),
            master_fields=dict(deck_config["master_fields"]),
            overlay_fields=list(deck_config["overlay_fields"]),
            anki_vocab=bool(deck_config.get("anki_vocab", False)),
        )
    return specs


def normalize_locale(locale: str) -> str:
    normalized = locale.strip().lower()
    manifest = load_manifest()
    supported = manifest.get("supported_locales", [])
    if normalized not in supported:
        raise ValueError(
            f"Unsupported locale {locale!r}. Choose from: {', '.join(supported)}",
        )
    return normalized


def is_overlay_locale(locale: str) -> bool:
    return normalize_locale(locale) in SUPPORTED_OVERLAY_LOCALES


def locale_label(locale: str) -> str:
    manifest = load_manifest()
    labels = manifest.get("locale_labels", {})
    return labels.get(normalize_locale(locale), locale)


def list_deck_names() -> list[str]:
    return list(get_deck_specs().keys())


def get_course_specs(manifest: dict[str, Any] | None = None) -> dict[str, CourseSpec]:
    data = manifest or load_manifest()
    courses: dict[str, CourseSpec] = {}
    for course_key, course_config in data.get("courses", {}).items():
        courses[course_key] = CourseSpec(
            key=course_key,
            label=course_config["label"],
            label_zh=course_config.get("label_zh", ""),
            deck_keys=list(course_config["deck_keys"]),
        )
    return courses


def get_aspect_map(manifest: dict[str, Any] | None = None) -> dict[str, str]:
    data = manifest or load_manifest()
    return dict(data.get("aspects", {}))


def aspect_for_deck(deck_key: str, manifest: dict[str, Any] | None = None) -> str:
    aspect_map = get_aspect_map(manifest)
    if deck_key not in aspect_map:
        raise KeyError(f"No aspect mapping for deck: {deck_key}")
    return aspect_map[deck_key]


def course_for_deck(deck_key: str, manifest: dict[str, Any] | None = None) -> str:
    for course_key, course_spec in get_course_specs(manifest).items():
        if deck_key in course_spec.deck_keys:
            return course_key
    raise KeyError(f"No course mapping for deck: {deck_key}")


def course_label_for_deck(deck_key: str, manifest: dict[str, Any] | None = None) -> str:
    course_key = course_for_deck(deck_key, manifest)
    return get_course_specs(manifest)[course_key].label


def list_supported_locales(manifest: dict[str, Any] | None = None) -> list[str]:
    data = manifest or load_manifest()
    return list(data.get("supported_locales", ["en"]))


def master_deck_name(manifest: dict[str, Any] | None = None) -> str:
    data = manifest or load_manifest()
    return data.get("master_deck_name", "PKU Spring 2026 Finals")


def anki_master_course_keys(manifest: dict[str, Any] | None = None) -> list[str]:
    """Courses included in export_master_anki / finals-master.apkg (excludes electives)."""
    data = manifest or load_manifest()
    configured = data.get("anki_master_courses")
    if configured:
        return list(configured)
    return [key for key in get_course_specs(data) if key != "xuanxiu"]


def multilocale_field_name(base: str, locale: str) -> str:
    """Anki field name, e.g. Meaning_en, UseCase_ru."""
    normalized = normalize_locale(locale)
    title_base = "".join(part.capitalize() for part in base.split("_"))
    return f"{title_base}_{normalized}"
