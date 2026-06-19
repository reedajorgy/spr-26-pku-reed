"""Load, normalize, and export Baokan extra study notes."""

from __future__ import annotations

import csv
import html
import io
import re
from pathlib import Path

import genanki

from apps.flashcards.anki_build import stable_id
from apps.flashcards.study_prefs import load_card_study_css

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV_PATH = REPO_ROOT / "outputs" / "baokan-extra.csv"
DEFAULT_DECK_NAME = "Baokan Extra"
CSV_COLUMNS = ("Front", "Back")

_DOUBLE_PUNCTUATION_RE = re.compile(r"([？！。，；：])[。．]")
_MULTI_BLANK_LINES_RE = re.compile(r"\n{3,}")
_MARKDOWN_ROW_START_RE = re.compile(r"^\|\s*(?P<front>[^|]+?)\s*\|\s*(?P<back>.*)$")
_MARKDOWN_ROW_CLOSE_RE = re.compile(r"^\|\s*$")


def _decode_csv_text(path: Path) -> str:
    raw_bytes = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def _normalize_cell(value: str) -> str:
    text = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    text = _DOUBLE_PUNCTUATION_RE.sub(r"\1", text)
    text = _MULTI_BLANK_LINES_RE.sub("\n\n", text)
    return text


def _normalize_front(value: str) -> str:
    text = _normalize_cell(value)
    text = re.sub(r"\s*/\s*", " / ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _strip_markdown_cell(value: str) -> str:
    text = value.strip()
    if text.endswith("|"):
        text = text[:-1].strip()
    return text


def _looks_like_python_export(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("import pandas") or stripped.startswith("data = [")


def _looks_like_markdown_table(text: str) -> bool:
    stripped = text.lstrip("\ufeff").lstrip()
    head = "\n".join(stripped.splitlines()[:5])
    if re.search(r"^\|\s*Front\s*\|\s*Back\s*\|", head, flags=re.MULTILINE | re.IGNORECASE):
        return True
    return bool(re.search(r"^\|\s*-{3,}\s*\|", head, flags=re.MULTILINE))


def _looks_like_csv_table(text: str) -> bool:
    stripped = text.lstrip("\ufeff").lstrip()
    first_line = stripped.splitlines()[0] if stripped else ""
    return first_line.startswith("Front,") or first_line.startswith('"Front"')


def _is_markdown_separator_row(line: str) -> bool:
    stripped = line.strip().lower()
    return stripped in ("| front | back |", "| --- | --- |") or "---" in stripped


def _load_rows_from_markdown_table(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    lines = text.splitlines()
    line_index = 0
    while line_index < len(lines):
        line = lines[line_index]
        stripped = line.strip()
        if not stripped.startswith("|") or _is_markdown_separator_row(stripped):
            line_index += 1
            continue

        row_match = _MARKDOWN_ROW_START_RE.match(line)
        if not row_match:
            line_index += 1
            continue

        front = _normalize_front(row_match.group("front"))
        back_parts: list[str] = []
        back_start = _strip_markdown_cell(row_match.group("back"))
        if back_start:
            back_parts.append(back_start)

        line_index += 1
        while line_index < len(lines):
            continuation = lines[line_index]
            continuation_stripped = continuation.strip()
            if _MARKDOWN_ROW_CLOSE_RE.fullmatch(continuation_stripped):
                line_index += 1
                break
            if _MARKDOWN_ROW_START_RE.match(continuation) and not _is_markdown_separator_row(
                continuation_stripped,
            ):
                break

            continuation_text = _strip_markdown_cell(continuation_stripped)
            if continuation_text:
                back_parts.append(continuation_text)
            line_index += 1

        back = _normalize_cell("\n".join(back_parts))
        if front or back:
            rows.append({"Front": front, "Back": back})

    return rows


def _load_rows_from_python_script(text: str) -> list[dict[str, str]]:
    namespace: dict[str, object] = {}
    sanitized = text
    sanitized = re.sub(
        r"df\.to_csv\([^)]*\)",
        "pass",
        sanitized,
        flags=re.MULTILINE,
    )
    sanitized = re.sub(
        r'print\("File exported successfully\."\)',
        "pass",
        sanitized,
    )
    exec(sanitized, namespace)  # noqa: S102 — trusted local export script input
    raw_rows = namespace.get("data")
    if not isinstance(raw_rows, list):
        raise ValueError("Python export script is missing a top-level data list.")
    rows: list[dict[str, str]] = []
    for raw_row in raw_rows:
        if not isinstance(raw_row, (list, tuple)) or len(raw_row) < 2:
            raise ValueError(f"Unexpected row shape in Python export: {raw_row!r}")
        rows.append(
            {
                "Front": _normalize_front(str(raw_row[0])),
                "Back": _normalize_cell(str(raw_row[1])),
            },
        )
    return rows


def _load_rows_from_csv_text(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames is None:
        raise ValueError("CSV file is missing a header row.")
    missing_columns = [column for column in CSV_COLUMNS if column not in reader.fieldnames]
    if missing_columns:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing_columns)}")
    rows: list[dict[str, str]] = []
    for row in reader:
        front = _normalize_front(row.get("Front", ""))
        back = _normalize_cell(row.get("Back", ""))
        if not front and not back:
            continue
        rows.append({"Front": front, "Back": back})
    return rows


def load_baokan_extra_rows(path: Path | None = None) -> list[dict[str, str]]:
    csv_path = path or DEFAULT_CSV_PATH
    text = _decode_csv_text(csv_path)
    if _looks_like_python_export(text):
        return _load_rows_from_python_script(text)
    if _looks_like_markdown_table(text):
        return _load_rows_from_markdown_table(text)
    if _looks_like_csv_table(text):
        return _load_rows_from_csv_text(text)
    raise ValueError(
        f"Unrecognized Baokan extra format in {csv_path}. "
        "Expected CSV (Front,Back), markdown table, or legacy Python export.",
    )


def write_baokan_extra_csv(
    rows: list[dict[str, str]],
    path: Path | None = None,
) -> Path:
    csv_path = path or DEFAULT_CSV_PATH
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "Front": row["Front"],
                    "Back": row["Back"],
                },
            )
    return csv_path


def normalize_baokan_extra_csv(
    source_path: Path | None = None,
    output_path: Path | None = None,
) -> tuple[Path, list[dict[str, str]]]:
    rows = load_baokan_extra_rows(source_path)
    if not rows:
        raise ValueError("No Baokan extra rows found to normalize.")
    destination = write_baokan_extra_csv(rows, output_path)
    return destination, rows


def _plain_text_to_html(text: str) -> str:
    escaped = html.escape(text, quote=False)
    return escaped.replace("\n", "<br>\n")


def _build_baokan_extra_model() -> genanki.Model:
    study_css = load_card_study_css()
    front = """
<div class="card-shell font-latin">
<div class="prompt">Baokan extra notes</div>
<div class="grammar-title text-zh">{{Front}}</div>
</div>
"""
    back = """
{{FrontSide}}
<hr class="answer-divider"/>
<div class="card-shell font-latin">
<div class="body-text text-zh">{{Back}}</div>
</div>
"""
    return genanki.Model(
        stable_id("spr-26-pku.baokan-extra.model"),
        "BaokanExtra",
        fields=[{"name": "Front"}, {"name": "Back"}],
        templates=[{"name": "BaokanExtra_Card", "qfmt": front, "afmt": back}],
        css=study_css,
    )


def build_baokan_extra_package(
    deck_name: str = DEFAULT_DECK_NAME,
    *,
    rows: list[dict[str, str]] | None = None,
    source_path: Path | None = None,
) -> genanki.Package:
    card_rows = rows if rows is not None else load_baokan_extra_rows(source_path)
    if not card_rows:
        raise ValueError("No Baokan extra rows found to export.")

    model = _build_baokan_extra_model()
    deck = genanki.Deck(stable_id("spr-26-pku.baokan-extra.deck"), deck_name)
    for row in card_rows:
        note = genanki.Note(
            model=model,
            fields=[
                row["Front"],
                _plain_text_to_html(row["Back"]),
            ],
            tags=["baokan", "extra"],
        )
        deck.add_note(note)

    package = genanki.Package(deck)
    package.models = [model]
    return package
