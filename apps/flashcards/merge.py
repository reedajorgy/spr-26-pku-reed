from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from apps.flashcards.locale_manifest import (
    DeckSpec,
    get_deck_specs,
    is_overlay_locale,
    list_supported_locales,
    multilocale_field_name,
    normalize_locale,
)
from apps.flashcards.paths import FINALS_DIR, locale_csv_path, master_csv_path


def _cell_to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(_cell_to_str(item) for item in value).strip()
    return str(value).strip()


def _decode_csv_text(path: Path) -> str:
    raw_bytes = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    text = _decode_csv_text(path)
    reader = csv.DictReader(io.StringIO(text, newline=""))
    rows: list[dict[str, str]] = []
    for row in reader:
        cleaned: dict[str, str] = {}
        for key, value in row.items():
            if key is None:
                continue
            cleaned[key] = _cell_to_str(value)
        rows.append(cleaned)
    return rows


def _join_key_from_row(row: dict[str, str], join_keys: list[str]) -> tuple[str, ...]:
    return tuple(row[key] for key in join_keys)


def _overlay_index(
    overlay_rows: list[dict[str, str]],
    join_keys: list[str],
) -> dict[tuple[str, ...], dict[str, str]]:
    index: dict[tuple[str, ...], dict[str, str]] = {}
    for row in overlay_rows:
        index[_join_key_from_row(row, join_keys)] = row
    return index


def merge_deck_rows(
    deck_name: str,
    locale: str = "en",
    *,
    finals_dir: Path | None = None,
    locales_dir: Path | None = None,
) -> list[dict[str, str]]:
    """
    Merge master CSV with locale overlay. Chinese and structural fields stay on master;
    translatable fields use overlay when locale is not en and a non-empty value exists.
    """
    normalized_locale = normalize_locale(locale)
    specs = get_deck_specs()
    if deck_name not in specs:
        raise KeyError(f"Unknown deck: {deck_name}")

    spec = specs[deck_name]
    base_dir = finals_dir or FINALS_DIR
    master_path = base_dir / spec.master_file
    master_rows = _read_csv_rows(master_path)

    overlay_rows: list[dict[str, str]] = []
    overlay_by_key: dict[tuple[str, ...], dict[str, str]] = {}
    if is_overlay_locale(normalized_locale):
        overlay_path = (locales_dir or base_dir / "locales") / normalized_locale / f"{deck_name}.csv"
        if overlay_path.is_file():
            overlay_rows = _read_csv_rows(overlay_path)
            overlay_by_key = _overlay_index(overlay_rows, spec.join_keys)

    positional_overlay = len(overlay_rows) == len(master_rows)
    merged: list[dict[str, str]] = []
    for index, master_row in enumerate(master_rows):
        output_row = dict(master_row)
        if positional_overlay:
            overlay_row = overlay_rows[index]
        else:
            overlay_row = overlay_by_key.get(_join_key_from_row(master_row, spec.join_keys), {})
        for overlay_field, master_field in spec.master_fields.items():
            master_value = master_row.get(master_field, "")
            overlay_value = overlay_row.get(overlay_field, "")
            if is_overlay_locale(normalized_locale) and overlay_value:
                output_row[master_field] = overlay_value
            else:
                output_row[master_field] = master_value
        merged.append(output_row)
    return merged


def merge_vocab_for_anki(
    deck_name: str,
    locale: str = "en",
    *,
    finals_dir: Path | None = None,
) -> list[dict[str, str]]:
    """Normalize merged vocab rows to Anki field names."""
    rows = merge_deck_rows(deck_name, locale, finals_dir=finals_dir)
    anki_rows: list[dict[str, str]] = []
    for row in rows:
        anki_rows.append(
            {
                "Chapter": row.get("Chapter", ""),
                "Hanzi": row.get("hanzi", ""),
                "Pinyin": row.get("pinyin", ""),
                "MandarinDef": row.get("mandarin_意义", ""),
                "English": row.get("英文意义", ""),
                "POS": row.get("词性", ""),
                "Collocations": row.get("搭配", ""),
                "Color": row.get("色彩", ""),
                "ExampleCN": row.get("example_sentence", ""),
                "ExampleEN": row.get("example_sentence_en", ""),
                "UsageNote": row.get("usage_note", ""),
                "CommonErrors": row.get("common_errors", ""),
                "RelatedWords": row.get("related_words", ""),
            },
        )
    return anki_rows


def merge_deck_to_records(
    deck_name: str,
    locale: str = "en",
    *,
    finals_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """API-friendly merged rows with both master and effective translation fields."""
    spec = get_deck_specs()[deck_name]
    rows = merge_deck_rows(deck_name, locale, finals_dir=finals_dir)
    records: list[dict[str, Any]] = []
    for row in rows:
        record: dict[str, Any] = {
            "deck": deck_name,
            "locale": normalize_locale(locale),
            "join": {key: row.get(key, "") for key in spec.join_keys},
            "master": dict(row),
            "translations": {
                overlay_field: row.get(master_field, "")
                for overlay_field, master_field in spec.master_fields.items()
            },
        }
        if spec.anki_vocab:
            record["anki"] = {
                "Chapter": row.get("Chapter", ""),
                "Hanzi": row.get("hanzi", ""),
                "Pinyin": row.get("pinyin", ""),
                "MandarinDef": row.get("mandarin_意义", ""),
                "English": row.get("英文意义", ""),
                "POS": row.get("词性", ""),
                "Collocations": row.get("搭配", ""),
                "Color": row.get("色彩", ""),
                "ExampleCN": row.get("example_sentence", ""),
                "ExampleEN": row.get("example_sentence_en", ""),
                "UsageNote": row.get("usage_note", ""),
                "CommonErrors": row.get("common_errors", ""),
                "RelatedWords": row.get("related_words", ""),
            }
        records.append(record)
    return records


def _effective_translation(
    master_row: dict[str, str],
    overlay_row: dict[str, str],
    overlay_field: str,
    master_field: str,
    locale: str,
) -> str:
    master_value = (master_row.get(master_field) or "").strip()
    if normalize_locale(locale) == "en":
        return master_value
    overlay_value = (overlay_row.get(overlay_field) or "").strip()
    return overlay_value if overlay_value else master_value


def merge_deck_rows_multilocale(
    deck_name: str,
    *,
    finals_dir: Path | None = None,
    locales_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Merge master with every supported locale overlay.

    Each row contains the full master row plus:
      translations[overlay_field][locale_code] -> effective gloss text
    """
    specs = get_deck_specs()
    if deck_name not in specs:
        raise KeyError(f"Unknown deck: {deck_name}")

    spec = specs[deck_name]
    base_dir = finals_dir or FINALS_DIR
    master_path = base_dir / spec.master_file
    master_rows = _read_csv_rows(master_path)
    locales_base = locales_dir or base_dir / "locales"
    supported_locales = list_supported_locales()

    overlay_by_locale: dict[str, list[dict[str, str]]] = {}
    overlay_index_by_locale: dict[str, dict[tuple[str, ...], dict[str, str]]] = {}
    positional_by_locale: dict[str, bool] = {}

    for locale_code in supported_locales:
        if not is_overlay_locale(locale_code):
            continue
        overlay_path = locales_base / locale_code / f"{deck_name}.csv"
        if not overlay_path.is_file():
            overlay_rows: list[dict[str, str]] = []
        else:
            overlay_rows = _read_csv_rows(overlay_path)
        overlay_by_locale[locale_code] = overlay_rows
        overlay_index_by_locale[locale_code] = _overlay_index(overlay_rows, spec.join_keys)
        positional_by_locale[locale_code] = len(overlay_rows) == len(master_rows)

    merged: list[dict[str, Any]] = []
    for index, master_row in enumerate(master_rows):
        translations: dict[str, dict[str, str]] = {
            overlay_field: {} for overlay_field in spec.overlay_fields
        }
        join_key = _join_key_from_row(master_row, spec.join_keys)

        for locale_code in supported_locales:
            if is_overlay_locale(locale_code):
                if positional_by_locale.get(locale_code, False):
                    overlay_row = overlay_by_locale[locale_code][index]
                else:
                    overlay_row = overlay_index_by_locale[locale_code].get(join_key, {})
            else:
                overlay_row = {}

            for overlay_field, master_field in spec.master_fields.items():
                translations[overlay_field][locale_code] = _effective_translation(
                    master_row,
                    overlay_row,
                    overlay_field,
                    master_field,
                    locale_code,
                )

        merged.append(
            {
                "master": dict(master_row),
                "translations": translations,
                "join": {key: master_row.get(key, "") for key in spec.join_keys},
            },
        )
    return merged


def _flatten_multilocale_translations(
    translations: dict[str, dict[str, str]],
    overlay_fields: list[str],
) -> dict[str, str]:
    flat: dict[str, str] = {}
    for overlay_field in overlay_fields:
        per_locale = translations.get(overlay_field, {})
        for locale_code, value in per_locale.items():
            flat[multilocale_field_name(overlay_field, locale_code)] = value
    return flat


def merge_vocab_for_anki_multilocale(
    deck_name: str,
    *,
    finals_dir: Path | None = None,
    locales_dir: Path | None = None,
) -> list[dict[str, str]]:
    """Normalize multilocale vocab rows to Anki field names (Meaning_en, etc.)."""
    spec = get_deck_specs()[deck_name]
    rows = merge_deck_rows_multilocale(
        deck_name,
        finals_dir=finals_dir,
        locales_dir=locales_dir,
    )
    anki_rows: list[dict[str, str]] = []
    for row in rows:
        master_row = row["master"]
        locale_fields = _flatten_multilocale_translations(row["translations"], spec.overlay_fields)
        anki_row: dict[str, str] = {
            "Chapter": master_row.get("Chapter", ""),
            "Hanzi": master_row.get("hanzi", ""),
            "Pinyin": master_row.get("pinyin", ""),
            "MandarinDef": master_row.get("mandarin_意义", ""),
            "POS": master_row.get("词性", ""),
            "Collocations": master_row.get("搭配", ""),
            "Color": master_row.get("色彩", ""),
            "ExampleCN": master_row.get("example_sentence", ""),
            "CommonErrors": master_row.get("common_errors", ""),
            "RelatedWords": master_row.get("related_words", ""),
            **locale_fields,
        }
        anki_rows.append(anki_row)
    return anki_rows


def merge_grammar_for_anki_multilocale(
    deck_key: str,
    *,
    finals_dir: Path | None = None,
    locales_dir: Path | None = None,
) -> list[dict[str, str]]:
    spec = get_deck_specs()[deck_key]
    rows = merge_deck_rows_multilocale(
        deck_key,
        finals_dir=finals_dir,
        locales_dir=locales_dir,
    )
    anki_rows: list[dict[str, str]] = []
    for row in rows:
        master_row = row["master"]
        locale_fields = _flatten_multilocale_translations(row["translations"], spec.overlay_fields)
        anki_row: dict[str, str] = {"Chapter": master_row.get("Chapter", ""), **locale_fields}

        if deck_key == "jingdu-qimo-grammar":
            anki_row.update(
                {
                    "GrammarPoint": master_row.get("Grammar Point", ""),
                    "Example1CN": master_row.get("Example 1", ""),
                    "Example2CN": master_row.get("Example 2", ""),
                    "Example3CN": master_row.get("Example 3", ""),
                },
            )
        elif deck_key == "kouyu-qimo-grammar":
            anki_row.update(
                {
                    "Pattern": master_row.get("Pattern Template", ""),
                    "Example1": master_row.get("Example 1", ""),
                    "Example2": master_row.get("Example 2", ""),
                    "Example3": master_row.get("Example 3", ""),
                    "Example4": master_row.get("Example 4", ""),
                    "Example5": master_row.get("Example 5", ""),
                },
            )
        elif deck_key == "jingdu-qimo-differences":
            anki_row.update(
                {
                    "WordPair": master_row.get("Word Pair", ""),
                    "Word": master_row.get("Word", ""),
                    "Example1CN": master_row.get("Example 1", ""),
                    "Example2CN": master_row.get("Example 2", ""),
                },
            )
        else:
            raise KeyError(f"Unsupported grammar/differences deck: {deck_key}")

        anki_rows.append(anki_row)
    return anki_rows
