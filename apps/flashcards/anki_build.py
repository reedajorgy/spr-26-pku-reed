from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import Callable

import genanki

from apps.flashcards.locale_manifest import get_deck_specs, locale_label, normalize_locale
from apps.flashcards.merge import merge_deck_rows, merge_vocab_for_anki
from apps.flashcards.paths import FINALS_DIR

from apps.flashcards.study_prefs import (
    STUDY_LAYOUT_CSS,
    locale_selector_html,
    reveal_toolbar_button,
    study_script_tag,
)

CARD_CSS = (
    """
.card {
  font-family: "PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
  font-size: 18px;
  color: #1a1a1a;
  background-color: #fafafa;
  text-align: left;
  line-height: 1.5;
}
.chapter-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
}
.prompt {
  font-size: 14px;
  color: #444;
  margin-bottom: 12px;
}
.hanzi-text { font-size: 42px; font-weight: 600; line-height: 1.2; }
.pinyin-text { font-size: 26px; color: #333; }
.translation-text { font-size: 20px; font-weight: 500; }
.mandarin-def { font-size: 16px; color: #555; margin-top: 6px; }
.meta-footer {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid #ddd;
  font-size: 14px;
  color: #444;
}
.badges { font-size: 13px; color: #555; margin-bottom: 8px; }
.meta-line { margin: 6px 0; }
.meta-label { font-weight: 600; color: #333; }
.production-front { font-size: 22px; font-weight: 500; margin: 16px 0; }
.grammar-title { font-size: 24px; font-weight: 600; margin-bottom: 8px; }
.body-text { font-size: 16px; margin: 8px 0; }
.pair-label { font-size: 16px; color: #666; font-weight: 400; }
"""
    + STUDY_LAYOUT_CSS
)


def stable_id(seed: str) -> int:
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()[:8]
    return int(digest, 16) & 0x7FFFFFFF


def parse_chapter_number(chapter_label: str) -> str:
    match = re.search(r"(\d+)", chapter_label.strip())
    if not match:
        raise ValueError(f"Could not parse chapter number from: {chapter_label!r}")
    return match.group(1)


def chapter_to_subdeck_name(chapter_label: str, deck_name: str) -> str:
    chapter_number = parse_chapter_number(chapter_label)
    return f"{deck_name}::Chapter_{chapter_number}"


def expand_collocations(collocations: str, hanzi: str) -> str:
    return collocations.replace("～", hanzi)


def translation_button_label(locale: str) -> str:
    normalized = normalize_locale(locale)
    if normalized == "en":
        return "English"
    return locale_label(normalized)


def build_vocab_model(locale: str) -> genanki.Model:
    translation_label = translation_button_label(locale)
    study_script = study_script_tag()
    meta_front = """
<div class="meta-footer">
  <div class="badges">{{{{POS}}}} · {{{{Color}}}}</div>
  <div class="meta-line"><span class="meta-label">搭配</span> {{{{Collocations}}}}</div>
</div>
"""
    example_block = """
<div id="example-block" class="example-block hidden">
  <div class="meta-line"><span class="meta-label">例句</span> {{{{ExampleCN}}}}</div>
  <div class="meta-line">{{{{ExampleEN}}}}</div>
  {{{{#UsageNote}}}}
  <div class="meta-line"><span class="meta-label">用法</span> {{{{UsageNote}}}}</div>
  {{{{/UsageNote}}}}
  {{{{#RelatedWords}}}}
  <div class="meta-line"><span class="meta-label">相关</span> {{{{RelatedWords}}}}</div>
  {{{{/RelatedWords}}}}
</div>
"""
    meta_back = """
<div class="meta-footer">
  <div class="badges">{{{{POS}}}} · {{{{Color}}}}</div>
  <div class="meta-line"><span class="meta-label">搭配</span> {{{{Collocations}}}}</div>
</div>
<div id="example-block" class="example-block">
  <div class="meta-line"><span class="meta-label">例句</span> {{{{ExampleCN}}}}</div>
  <div class="meta-line">{{{{ExampleEN}}}}</div>
  {{{{#UsageNote}}}}
  <div class="meta-line"><span class="meta-label">用法</span> {{{{UsageNote}}}}</div>
  {{{{/UsageNote}}}}
  {{{{#RelatedWords}}}}
  <div class="meta-line"><span class="meta-label">相关</span> {{{{RelatedWords}}}}</div>
  {{{{/RelatedWords}}}}
</div>
"""
    toolbar = f"""
<div class="card-toolbar">
  {reveal_toolbar_button("hanzi-block", "汉字")}
  {reveal_toolbar_button("pinyin-block", "拼音")}
  {reveal_toolbar_button("translation-block", translation_label)}
  {reveal_toolbar_button("example-block", "例句")}
</div>
"""
    toggle_front = f"""
<div class="card-shell">
<div class="chapter-label">{{{{Chapter}}}}</div>
{locale_selector_html()}
<div class="prompt">Reveal hints as needed, then grade yourself.</div>
{toolbar}
<div id="hanzi-block" class="reveal-block hidden">
  <div class="hanzi-text">{{{{Hanzi}}}}</div>
</div>
<div id="pinyin-block" class="reveal-block hidden">
  <div class="pinyin-text">{{{{Pinyin}}}}</div>
</div>
<div id="translation-block" class="reveal-block hidden">
  <div class="translation-text">{{{{English}}}}</div>
  <div class="mandarin-def">{{{{MandarinDef}}}}</div>
</div>
{meta_front}
{example_block}
</div>
{study_script}
"""
    toggle_back = f"""
{{{{FrontSide}}}}
<hr class="answer-divider"/>
<script>spr26RevealOnBack();</script>
{study_script}
"""
    production_front = f"""
<div class="card-shell">
<div class="chapter-label">{{{{Chapter}}}}</div>
{locale_selector_html()}
<div class="badges">{{{{Color}}}}</div>
<div class="production-front">{{{{English}}}}</div>
</div>
{study_script}
"""
    production_back = f"""
<div class="card-shell">
<div class="chapter-label">{{{{Chapter}}}}</div>
<div class="hanzi-text">{{{{Hanzi}}}}</div>
<div class="pinyin-text">{{{{Pinyin}}}}</div>
<div class="mandarin-def">{{{{MandarinDef}}}}</div>
{meta_back}
</div>
{study_script}
"""
    field_names = [
        "Chapter",
        "Hanzi",
        "Pinyin",
        "MandarinDef",
        "English",
        "POS",
        "Collocations",
        "Color",
        "ExampleCN",
        "ExampleEN",
        "UsageNote",
        "CommonErrors",
        "RelatedWords",
    ]
    model_id = stable_id(f"spr-26-pku.vocab.model.{locale}")
    return genanki.Model(
        model_id,
        f"FinalsVocab_{locale}",
        fields=[{"name": name} for name in field_names],
        templates=[
            {"name": "Vocab_Toggle", "qfmt": toggle_front, "afmt": toggle_back},
            {
                "name": "Vocab_Production",
                "qfmt": production_front,
                "afmt": production_back,
            },
        ],
        css=CARD_CSS,
    )


def build_grammar_model(deck_key: str, locale: str) -> genanki.Model:
    if deck_key == "jingdu-qimo-grammar":
        fields = [
            "Chapter",
            "GrammarPoint",
            "UseCase",
            "Example1CN",
            "Example1EN",
            "Example2CN",
            "Example2EN",
            "Example3CN",
            "Example3EN",
        ]
        front = """
<div class="chapter-label">{{Chapter}}</div>
<div class="grammar-title">{{GrammarPoint}}</div>
<div class="body-text">{{UseCase}}</div>
"""
        back = """
<div class="chapter-label">{{Chapter}}</div>
<div class="grammar-title">{{GrammarPoint}}</div>
<div class="body-text">{{UseCase}}</div>
<hr/>
<div class="meta-line"><span class="meta-label">例1</span> {{Example1CN}}</div>
<div class="meta-line">{{Example1EN}}</div>
<div class="meta-line"><span class="meta-label">例2</span> {{Example2CN}}</div>
<div class="meta-line">{{Example2EN}}</div>
<div class="meta-line"><span class="meta-label">例3</span> {{Example3CN}}</div>
<div class="meta-line">{{Example3EN}}</div>
"""
    else:
        fields = [
            "Chapter",
            "Pattern",
            "Explanation",
            "Example1",
            "Example2",
            "Example3",
            "Example4",
            "Example5",
        ]
        front = """
<div class="chapter-label">{{Chapter}}</div>
<div class="grammar-title">{{Pattern}}</div>
<div class="body-text">{{Explanation}}</div>
"""
        back = """
<div class="chapter-label">{{Chapter}}</div>
<div class="grammar-title">{{Pattern}}</div>
<div class="body-text">{{Explanation}}</div>
<hr/>
<div class="meta-line">{{Example1}}</div>
<div class="meta-line">{{Example2}}</div>
<div class="meta-line">{{Example3}}</div>
<div class="meta-line">{{Example4}}</div>
<div class="meta-line">{{Example5}}</div>
"""
    model_id = stable_id(f"spr-26-pku.grammar.{deck_key}.model.{locale}")
    return genanki.Model(
        model_id,
        f"FinalsGrammar_{deck_key}_{locale}",
        fields=[{"name": name} for name in fields],
        templates=[{"name": "Grammar_Card", "qfmt": front, "afmt": back}],
        css=CARD_CSS,
    )


def build_differences_model(locale: str) -> genanki.Model:
    fields = [
        "Chapter",
        "WordPair",
        "Word",
        "Nuance",
        "GrammarNotes",
        "Example1CN",
        "Example1EN",
        "Example2CN",
        "Example2EN",
    ]
    front = """
<div class="chapter-label">{{Chapter}}</div>
<div class="grammar-title">{{Word}} <span style="font-size:16px;color:#666">({{WordPair}})</span></div>
<div class="body-text">{{Nuance}}</div>
"""
    back = """
<div class="chapter-label">{{Chapter}}</div>
<div class="grammar-title">{{Word}}</div>
<div class="body-text">{{Nuance}}</div>
<div class="body-text"><b>Grammar:</b> {{GrammarNotes}}</div>
<hr/>
<div class="meta-line">{{Example1CN}}</div>
<div class="meta-line">{{Example1EN}}</div>
<div class="meta-line">{{Example2CN}}</div>
<div class="meta-line">{{Example2EN}}</div>
"""
    model_id = stable_id(f"spr-26-pku.differences.model.{locale}")
    return genanki.Model(
        model_id,
        f"FinalsDifferences_{locale}",
        fields=[{"name": name} for name in fields],
        templates=[{"name": "Difference_Card", "qfmt": front, "afmt": back}],
        css=CARD_CSS,
    )


def row_to_vocab_fields(row: dict[str, str]) -> list[str]:
    hanzi = row["Hanzi"]
    return [
        row["Chapter"],
        hanzi,
        row["Pinyin"],
        row["MandarinDef"],
        row["English"],
        row["POS"],
        expand_collocations(row["Collocations"], hanzi),
        row["Color"],
        row["ExampleCN"],
        row["ExampleEN"],
        row["UsageNote"],
        row["CommonErrors"],
        row["RelatedWords"],
    ]


def row_to_jingdu_grammar_fields(row: dict[str, str]) -> list[str]:
    return [
        row.get("Chapter", ""),
        row.get("Grammar Point", ""),
        row.get("Use Case / Meaning", ""),
        row.get("Example 1", ""),
        row.get("Example 1 English", ""),
        row.get("Example 2", ""),
        row.get("Example 2 English", ""),
        row.get("Example 3", ""),
        row.get("Example 3 English", ""),
    ]


def row_to_kouyu_grammar_fields(row: dict[str, str]) -> list[str]:
    return [
        row.get("Chapter", ""),
        row.get("Pattern Template", ""),
        row.get("English Explanation", ""),
        row.get("Example 1", ""),
        row.get("Example 2", ""),
        row.get("Example 3", ""),
        row.get("Example 4", ""),
        row.get("Example 5", ""),
    ]


def row_to_differences_fields(row: dict[str, str]) -> list[str]:
    return [
        row.get("Chapter", ""),
        row.get("Word Pair", ""),
        row.get("Word", ""),
        row.get("Nuance & Use Cases", ""),
        row.get("Grammar Considerations", ""),
        row.get("Example 1", ""),
        row.get("Example 1 English", ""),
        row.get("Example 2", ""),
        row.get("Example 2 English", ""),
    ]


def build_vocab_package(
    deck_csv_name: str,
    locale: str,
    parent_deck_name: str,
    *,
    finals_dir: Path | None = None,
    tag_prefix: str,
) -> genanki.Package:
    rows = merge_vocab_for_anki(deck_csv_name, locale, finals_dir=finals_dir)
    for row in rows:
        row["Collocations"] = expand_collocations(row["Collocations"], row["Hanzi"])
    model = build_vocab_model(locale)
    return _build_package_from_rows(
        rows,
        model,
        parent_deck_name,
        tag_prefix,
        lambda row: row_to_vocab_fields(row),
        cards_per_note=2,
        deck_seed_prefix=deck_csv_name,
    )


def build_grammar_package(
    deck_key: str,
    locale: str,
    parent_deck_name: str,
    *,
    finals_dir: Path | None = None,
) -> genanki.Package:
    rows = merge_deck_rows(deck_key, locale, finals_dir=finals_dir)
    model = build_grammar_model(deck_key, locale)
    if deck_key == "jingdu-qimo-grammar":
        field_fn = row_to_jingdu_grammar_fields
        tag_prefix = "jingdu"
    else:
        field_fn = row_to_kouyu_grammar_fields
        tag_prefix = "kouyu"
    return _build_package_from_rows(
        rows,
        model,
        parent_deck_name,
        tag_prefix,
        field_fn,
        cards_per_note=1,
        deck_seed_prefix=deck_key,
    )


def build_differences_package(
    locale: str,
    parent_deck_name: str,
    *,
    finals_dir: Path | None = None,
) -> genanki.Package:
    rows = merge_deck_rows("jingdu-qimo-differences", locale, finals_dir=finals_dir)
    model = build_differences_model(locale)
    return _build_package_from_rows(
        rows,
        model,
        parent_deck_name,
        "jingdu",
        row_to_differences_fields,
        cards_per_note=1,
        deck_seed_prefix="jingdu-qimo-differences",
    )


def _build_package_from_rows(
    rows: list[dict[str, str]],
    model: genanki.Model,
    parent_deck_name: str,
    tag_prefix: str,
    field_fn: Callable[[dict[str, str]], list[str]],
    *,
    cards_per_note: int,
    deck_seed_prefix: str,
) -> genanki.Package:
    decks_by_name: dict[str, genanki.Deck] = {}
    for row in rows:
        chapter = row.get("Chapter", row.get("chapter", ""))
        if not chapter:
            continue
        subdeck_name = chapter_to_subdeck_name(chapter, parent_deck_name)
        if subdeck_name not in decks_by_name:
            deck_id = stable_id(f"spr-26-pku.deck.{deck_seed_prefix}.{subdeck_name}")
            decks_by_name[subdeck_name] = genanki.Deck(deck_id, subdeck_name)
        chapter_number = parse_chapter_number(chapter)
        tags = [tag_prefix, "qimo", f"ch{chapter_number}"]
        note = genanki.Note(model=model, fields=field_fn(row), tags=tags)
        decks_by_name[subdeck_name].add_note(note)

    package = genanki.Package(list(decks_by_name.values())[0])
    package.models = [model]
    package.decks = list(decks_by_name.values())
    return package


def build_deck_package(
    deck_key: str,
    locale: str,
    parent_deck_name: str,
    *,
    finals_dir: Path | None = None,
) -> genanki.Package:
    specs = get_deck_specs()
    spec = specs[deck_key]
    if spec.anki_vocab:
        tag = "kouyu" if deck_key.startswith("kouyu") else "jingdu"
        return build_vocab_package(
            deck_key,
            locale,
            parent_deck_name,
            finals_dir=finals_dir,
            tag_prefix=tag,
        )
    if deck_key == "jingdu-qimo-differences":
        return build_differences_package(locale, parent_deck_name, finals_dir=finals_dir)
    return build_grammar_package(deck_key, locale, parent_deck_name, finals_dir=finals_dir)


def summarize_package(rows: list[dict[str, str]], cards_per_note: int) -> tuple[int, int, Counter[str]]:
    chapter_counts = Counter(row.get("Chapter", "") for row in rows if row.get("Chapter"))
    note_count = len([row for row in rows if row.get("Chapter")])
    return note_count, note_count * cards_per_note, chapter_counts
