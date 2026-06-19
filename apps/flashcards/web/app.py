from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from apps.flashcards.hierarchy import build_hierarchy_summary, deck_keys_for_filters
from apps.flashcards.locale_manifest import (
    aspect_for_deck,
    course_label_for_deck,
    get_aspect_map,
    get_course_specs,
    get_deck_specs,
    list_deck_names,
    load_manifest,
    locale_label,
    normalize_locale,
)
from apps.flashcards.merge import merge_deck_to_records
from apps.flashcards.paths import FINALS_DIR, MANIFEST_PATH
from apps.flashcards.study_prefs import study_prefs_api_payload

STATIC_DIR = Path(__file__).resolve().parent / "static"
CARD_STUDY_CSS_PATH = Path(__file__).resolve().parents[1] / "static" / "card_study.css"

app = FastAPI(title="Reed's Finals Flashcards", version="1.0.0")


@app.get("/static/card_study.css", include_in_schema=False)
def shared_card_study_css() -> FileResponse:
    return FileResponse(CARD_STUDY_CSS_PATH, media_type="text/css")


@app.get("/api/study-prefs")
def api_study_prefs() -> dict[str, Any]:
    return study_prefs_api_payload()


@app.get("/api/locales")
def api_locales() -> dict[str, Any]:
    manifest = load_manifest()
    codes = manifest.get("supported_locales", [])
    return {
        "default": manifest.get("default_locale", "en"),
        "locales": [
            {"code": code, "label": locale_label(code)}
            for code in codes
        ],
    }


@app.get("/api/courses")
def api_courses() -> dict[str, Any]:
    courses = []
    for course_key, course_spec in get_course_specs().items():
        courses.append(
            {
                "id": course_key,
                "label": course_spec.label,
                "label_zh": course_spec.label_zh,
                "deck_keys": course_spec.deck_keys,
            },
        )
    return {"courses": courses}


@app.get("/api/aspects")
def api_aspects() -> dict[str, Any]:
    aspect_map = get_aspect_map()
    unique_aspects = sorted(set(aspect_map.values()))
    aspect_labels = {
        "Vocab": "Vocabulary",
        "Grammar": "Grammar",
        "Word_Differences": "Word differences",
    }
    return {
        "aspects": [
            {
                "id": aspect_name,
                "label": aspect_labels.get(aspect_name, aspect_name.replace("_", " ")),
                "deck_keys": [
                    deck for deck, name in aspect_map.items() if name == aspect_name
                ],
            }
            for aspect_name in unique_aspects
        ],
    }


@app.get("/api/hierarchy")
def api_hierarchy() -> dict[str, Any]:
    return build_hierarchy_summary(finals_dir=FINALS_DIR)


@app.get("/api/decks")
def api_decks() -> dict[str, Any]:
    specs = get_deck_specs()
    aspect_labels = {
        "Vocab": "Vocabulary",
        "Grammar": "Grammar",
        "Word_Differences": "Word differences",
    }
    return {
        "decks": [
            {
                "id": deck_name,
                "label": (
                    f"{course_label_for_deck(deck_name)} · "
                    f"{aspect_labels.get(aspect_for_deck(deck_name), aspect_for_deck(deck_name))}"
                ),
                "course": course_label_for_deck(deck_name),
                "aspect": aspect_labels.get(
                    aspect_for_deck(deck_name),
                    aspect_for_deck(deck_name),
                ),
                "master_file": spec.master_file,
                "anki_vocab": spec.anki_vocab,
            }
            for deck_name, spec in specs.items()
        ],
    }


def _resolve_deck_keys(
    deck: str | None,
    course: str | None,
    aspect: str | None,
) -> list[str]:
    if deck:
        if deck not in list_deck_names():
            raise HTTPException(status_code=404, detail=f"Unknown deck: {deck}")
        return [deck]
    filtered = deck_keys_for_filters(course, aspect)
    if filtered is not None and not filtered:
        raise HTTPException(status_code=404, detail="No decks match filters")
    if filtered is not None:
        return filtered
    return list_deck_names()


@app.get("/api/cards")
def api_cards(
    deck: str | None = Query(None, description="Deck id from manifest"),
    course: str | None = Query(None, description="Course key: kouyu or jingdu"),
    aspect: str | None = Query(None, description="Aspect: Vocab, Grammar, Word_Differences"),
    locale: str = Query("en"),
    chapter: str | None = Query(None, description="Filter e.g. Chapter 5"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    try:
        normalized_locale = normalize_locale(locale)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    deck_keys = _resolve_deck_keys(deck, course, aspect)
    records: list[dict[str, Any]] = []
    for deck_key in deck_keys:
        records.extend(
            merge_deck_to_records(deck_key, normalized_locale, finals_dir=FINALS_DIR),
        )

    if chapter:
        records = [
            record
            for record in records
            if record["join"].get("Chapter") == chapter
        ]

    total = len(records)
    page = records[offset : offset + limit]
    return {
        "deck": deck,
        "course": course,
        "aspect": aspect,
        "deck_keys": deck_keys,
        "locale": normalized_locale,
        "total": total,
        "offset": offset,
        "limit": limit,
        "cards": page,
    }


@app.get("/api/chapters")
def api_chapters(
    deck: str | None = Query(None),
    course: str | None = Query(None),
    aspect: str | None = Query(None),
) -> dict[str, Any]:
    deck_keys = _resolve_deck_keys(deck, course, aspect)
    chapters: set[str] = set()
    for deck_key in deck_keys:
        records = merge_deck_to_records(deck_key, "en", finals_dir=FINALS_DIR)
        for record in records:
            chapter_label = record["join"].get("Chapter", "")
            if chapter_label:
                chapters.add(chapter_label)
    ordered = sorted(
        chapters,
        key=lambda label: int("".join(filter(str.isdigit, label)) or "0"),
    )
    return {"deck": deck, "course": course, "aspect": aspect, "chapters": ordered}


@app.get("/api/deploy-check")
def api_deploy_check() -> dict[str, Any]:
    """Lightweight health check for Vercel/local deploy verification."""
    import sys

    overlay_locales = [
        code
        for code in load_manifest().get("supported_locales", [])
        if code != "en"
    ]
    overlay_count = sum(
        1
        for locale_code in overlay_locales
        for deck_name in get_deck_specs()
        if (FINALS_DIR / "locales" / locale_code / f"{deck_name}.csv").is_file()
    )
    python_deps_dir = FINALS_DIR.parent / "python_deps"
    diagnostics = {
        "status": "ok",
        "app_title": app.title,
        "repo_root": str(FINALS_DIR.parent),
        "python_deps_exists": python_deps_dir.is_dir(),
        "finals_dir_exists": FINALS_DIR.is_dir(),
        "manifest_exists": MANIFEST_PATH.is_file(),
        "static_index_exists": (STATIC_DIR / "index.html").is_file(),
        "deck_count": len(get_deck_specs()),
        "overlay_csv_count": overlay_count,
        "python_version": sys.version,
    }
    try:
        import fastapi as fastapi_module

        diagnostics["fastapi_version"] = fastapi_module.__version__
    except ImportError as error:
        diagnostics["fastapi_version"] = f"missing: {error}"
        diagnostics["status"] = "degraded"

    return diagnostics


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.png", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def main() -> None:
    import uvicorn

    uvicorn.run("apps.flashcards.web.app:app", host="127.0.0.1", port=8765, reload=False)


if __name__ == "__main__":
    main()
