from __future__ import annotations

from collections import Counter
from pathlib import Path

import genanki

from apps.flashcards.anki_build import (
    CARD_CSS,
    expand_collocations,
    parse_chapter_number,
    stable_id,
)
from apps.flashcards.locale_manifest import (
    aspect_for_deck,
    course_for_deck,
    course_label_for_deck,
    get_course_specs,
    get_deck_specs,
    list_supported_locales,
    master_deck_name,
    multilocale_field_name,
)
from apps.flashcards.merge import (
    merge_grammar_for_anki_multilocale,
    merge_vocab_for_anki_multilocale,
)
from apps.flashcards.paths import FINALS_DIR
from apps.flashcards.study_prefs import (
    locale_selector_html,
    reveal_toolbar_button,
    study_script_tag,
)

STUDY_CSS = CARD_CSS


def aspect_subdeck_name(
    root_name: str,
    course_label: str,
    chapter_label: str,
    aspect: str,
) -> str:
    chapter_number = parse_chapter_number(chapter_label)
    return f"{root_name}::{course_label}::Chapter_{chapter_number}::{aspect}"


def _locale_blocks_html(field_prefix: str, inner_html: str) -> str:
    """field_prefix is title-cased base e.g. Meaning from overlay field 'meaning'."""
    blocks = []
    for locale_code in list_supported_locales():
        field_name = f"{field_prefix}_{locale_code}"
        blocks.append(
            f'<div class="locale-block" data-locale="{locale_code}">'
            f"{inner_html.replace('FIELD', '{{' + field_name + '}}')}"
            f"</div>",
        )
    return "\n".join(blocks)


def _title_base_from_overlay(overlay_field: str) -> str:
    return "".join(part.capitalize() for part in overlay_field.split("_"))


def _multilocale_field_names(overlay_fields: list[str]) -> list[str]:
    names: list[str] = []
    for overlay_field in overlay_fields:
        title_base = _title_base_from_overlay(overlay_field)
        for locale_code in list_supported_locales():
            names.append(f"{title_base}_{locale_code}")
    return names


def _vocab_example_en_blocks() -> str:
    blocks = []
    for locale_code in list_supported_locales():
        blocks.append(
            f'<div class="locale-block" data-locale="{locale_code}">'
            f'<div class="meta-line">{{{{ExampleEn_{locale_code}}}}}</div></div>',
        )
    return "\n".join(blocks)


def _vocab_usage_blocks() -> str:
    blocks = []
    for locale_code in list_supported_locales():
        blocks.append(
            f"{{{{#UsageNote_{locale_code}}}}}"
            f'<div class="locale-block" data-locale="{locale_code}">'
            f'<div class="meta-line"><span class="meta-label">用法</span> '
            f"{{{{UsageNote_{locale_code}}}}}</div></div>"
            f"{{{{/UsageNote_{locale_code}}}}}",
        )
    return "\n".join(blocks)


def _vocab_meta_front() -> str:
    return """
<div class="meta-footer">
  <div class="badges">{{{{POS}}}} · {{{{Color}}}}</div>
  <div class="meta-line"><span class="meta-label">搭配</span> {{{{Collocations}}}}</div>
</div>
"""


def _vocab_example_block() -> str:
    return f"""
<div id="example-block" class="example-block hidden">
  <div class="meta-line"><span class="meta-label">例句</span> {{{{ExampleCN}}}}</div>
  {_vocab_example_en_blocks()}
  {_vocab_usage_blocks()}
  {{{{#CommonErrors}}}}
  <div class="meta-line"><span class="meta-label">易错</span> {{{{CommonErrors}}}}</div>
  {{{{/CommonErrors}}}}
  {{{{#RelatedWords}}}}
  <div class="meta-line"><span class="meta-label">相关</span> {{{{RelatedWords}}}}</div>
  {{{{/RelatedWords}}}}
</div>
"""


def _vocab_meta_back_visible() -> str:
    return f"""
<div class="meta-footer">
  <div class="badges">{{{{POS}}}} · {{{{Color}}}}</div>
  <div class="meta-line"><span class="meta-label">搭配</span> {{{{Collocations}}}}</div>
</div>
<div id="example-block" class="example-block">
  <div class="meta-line"><span class="meta-label">例句</span> {{{{ExampleCN}}}}</div>
  {_vocab_example_en_blocks()}
  {_vocab_usage_blocks()}
  {{{{#CommonErrors}}}}
  <div class="meta-line"><span class="meta-label">易错</span> {{{{CommonErrors}}}}</div>
  {{{{/CommonErrors}}}}
  {{{{#RelatedWords}}}}
  <div class="meta-line"><span class="meta-label">相关</span> {{{{RelatedWords}}}}</div>
  {{{{/RelatedWords}}}}
</div>
"""


def _vocab_toggle_toolbar() -> str:
    return f"""
<div class="card-toolbar">
  {reveal_toolbar_button("hanzi-block", "汉字")}
  {reveal_toolbar_button("pinyin-block", "拼音")}
  {reveal_toolbar_button("translation-block", "Gloss")}
  {reveal_toolbar_button("example-block", "例句")}
</div>
"""


def _card_opening() -> str:
    return f"""
<div class="card-shell">
<div class="chapter-label">{{{{Chapter}}}}</div>
{locale_selector_html()}
"""


def build_multilocale_vocab_model() -> genanki.Model:
    overlay_fields = ["meaning", "example_en", "usage_note"]
    meaning_blocks = _locale_blocks_html(
        "Meaning",
        '<div class="translation-text">FIELD</div>',
    )
    study_script = study_script_tag()
    toggle_front = f"""
{_card_opening()}
<div class="prompt">Reveal hints as needed, then grade yourself.</div>
{_vocab_toggle_toolbar()}
<div id="hanzi-block" class="reveal-block hidden">
  <div class="hanzi-text">{{{{Hanzi}}}}</div>
</div>
<div id="pinyin-block" class="reveal-block hidden">
  <div class="pinyin-text">{{{{Pinyin}}}}</div>
</div>
<div id="translation-block" class="reveal-block hidden">
  {meaning_blocks}
  <div class="mandarin-def">{{{{MandarinDef}}}}</div>
</div>
{_vocab_meta_front()}
{_vocab_example_block()}
</div>
{study_script}
"""
    toggle_back = f"""
{{{{FrontSide}}}}
<hr class="answer-divider"/>
<script>spr26RevealOnBack();</script>
{study_script}
"""
    production_meaning_blocks = meaning_blocks.replace(
        "translation-text",
        "production-front",
    )
    production_front = f"""
{_card_opening()}
<div class="badges">{{{{Color}}}}</div>
<div class="card-body">
{production_meaning_blocks}
</div>
</div>
{study_script}
"""
    production_back = f"""
<div class="card-shell">
<div class="chapter-label">{{{{Chapter}}}}</div>
<div class="hanzi-text">{{{{Hanzi}}}}</div>
<div class="pinyin-text">{{{{Pinyin}}}}</div>
<div class="mandarin-def">{{{{MandarinDef}}}}</div>
{_vocab_meta_back_visible()}
</div>
{study_script}
"""
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
        *_multilocale_field_names(overlay_fields),
    ]
    model_id = stable_id("spr-26-pku.vocab.model.multilocale")
    return genanki.Model(
        model_id,
        "FinalsVocab_Multilocale",
        fields=[{"name": name} for name in field_names],
        templates=[
            {"name": "Vocab_Toggle", "qfmt": toggle_front, "afmt": toggle_back},
            {
                "name": "Vocab_Production",
                "qfmt": production_front,
                "afmt": production_back,
            },
        ],
        css=STUDY_CSS,
    )


def _grammar_locale_body(overlay_fields: list[str], inner_template: str) -> str:
    parts = []
    for overlay_field in overlay_fields:
        title_base = _title_base_from_overlay(overlay_field)
        for locale_code in list_supported_locales():
            field_name = f"{title_base}_{locale_code}"
            block_inner = inner_template.replace("FIELD", "{{" + field_name + "}}")
            parts.append(
                f'<div class="locale-block" data-locale="{locale_code}">{block_inner}</div>',
            )
    return "\n".join(parts)


def _jingdu_grammar_example_sections() -> str:
    example_sections = ""
    for example_index in range(1, 4):
        cn_field = f"Example{example_index}CN"
        en_overlay = f"example_{example_index}_en"
        title_base = _title_base_from_overlay(en_overlay)
        en_blocks = []
        for locale_code in list_supported_locales():
            en_blocks.append(
                f'<div class="locale-block" data-locale="{locale_code}">'
                f'<div class="meta-line">{{{{{title_base}_{locale_code}}}}}</div></div>',
            )
        example_sections += f"""
<div class="meta-line"><span class="meta-label">例{example_index}</span> {{{{{cn_field}}}}}</div>
{"".join(en_blocks)}
"""
    return example_sections


def build_multilocale_jingdu_grammar_model() -> genanki.Model:
    overlay_fields = ["use_case", "example_1_en", "example_2_en", "example_3_en"]
    use_case_blocks = _grammar_locale_body(
        overlay_fields[:1],
        '<div class="body-text">FIELD</div>',
    )
    example_sections = _jingdu_grammar_example_sections()
    study_script = study_script_tag()
    front = f"""
{_card_opening()}
<div class="grammar-title">{{{{GrammarPoint}}}}</div>
{use_case_blocks}
<div class="card-toolbar">
  {reveal_toolbar_button("examples-block", "例句")}
</div>
<div id="examples-block" class="example-block hidden">
{example_sections}
</div>
</div>
{study_script}
"""
    back = f"""
<div class="card-shell">
<div class="chapter-label">{{{{Chapter}}}}</div>
<div class="grammar-title">{{{{GrammarPoint}}}}</div>
{use_case_blocks}
<hr class="answer-divider"/>
<div id="examples-block" class="example-block">
{example_sections}
</div>
</div>
{study_script}
"""
    field_names = [
        "Chapter",
        "GrammarPoint",
        "Example1CN",
        "Example2CN",
        "Example3CN",
        *_multilocale_field_names(overlay_fields),
    ]
    return genanki.Model(
        stable_id("spr-26-pku.grammar.jingdu.multilocale"),
        "FinalsGrammar_Jingdu_Multilocale",
        fields=[{"name": name} for name in field_names],
        templates=[{"name": "Grammar_Card", "qfmt": front, "afmt": back}],
        css=STUDY_CSS,
    )


def build_multilocale_kouyu_grammar_model() -> genanki.Model:
    overlay_fields = ["explanation"]
    explanation_blocks = _grammar_locale_body(
        overlay_fields,
        '<div class="body-text">FIELD</div>',
    )
    kouyu_examples = """
<div class="meta-line">{{Example1}}</div>
<div class="meta-line">{{Example2}}</div>
<div class="meta-line">{{Example3}}</div>
<div class="meta-line">{{Example4}}</div>
<div class="meta-line">{{Example5}}</div>
"""
    study_script = study_script_tag()
    front = f"""
{_card_opening()}
<div class="grammar-title">{{{{Pattern}}}}</div>
{explanation_blocks}
<div class="card-toolbar">
  {reveal_toolbar_button("examples-block", "例句")}
</div>
<div id="examples-block" class="example-block hidden">
{kouyu_examples}
</div>
</div>
{study_script}
"""
    back = f"""
<div class="card-shell">
<div class="chapter-label">{{{{Chapter}}}}</div>
<div class="grammar-title">{{{{Pattern}}}}</div>
{explanation_blocks}
<hr class="answer-divider"/>
<div id="examples-block" class="example-block">
{kouyu_examples}
</div>
</div>
{study_script}
"""
    field_names = [
        "Chapter",
        "Pattern",
        "Example1",
        "Example2",
        "Example3",
        "Example4",
        "Example5",
        *_multilocale_field_names(overlay_fields),
    ]
    return genanki.Model(
        stable_id("spr-26-pku.grammar.kouyu.multilocale"),
        "FinalsGrammar_Kouyu_Multilocale",
        fields=[{"name": name} for name in field_names],
        templates=[{"name": "Grammar_Card", "qfmt": front, "afmt": back}],
        css=STUDY_CSS,
    )


def build_multilocale_differences_model() -> genanki.Model:
    overlay_fields = ["nuance", "grammar_notes", "example_1_en", "example_2_en"]
    nuance_blocks = _grammar_locale_body(
        ["nuance"],
        '<div class="body-text">FIELD</div>',
    )
    grammar_blocks = _grammar_locale_body(
        ["grammar_notes"],
        '<div class="body-text"><b>Grammar:</b> FIELD</div>',
    )
    example_sections = ""
    for example_index in range(1, 3):
        cn_field = f"Example{example_index}CN"
        en_overlay = f"example_{example_index}_en"
        title_base = _title_base_from_overlay(en_overlay)
        en_blocks = []
        for locale_code in list_supported_locales():
            en_blocks.append(
                f'<div class="locale-block" data-locale="{locale_code}">'
                f'<div class="meta-line">{{{{{title_base}_{locale_code}}}}}</div></div>',
            )
        example_sections += f"""
<div class="meta-line">{{{{{cn_field}}}}}</div>
{"".join(en_blocks)}
"""
    study_script = study_script_tag()
    front = f"""
{_card_opening()}
<div class="grammar-title">{{{{Word}}}} <span class="pair-label">({{{{WordPair}}}})</span></div>
{nuance_blocks}
<div class="card-toolbar">
  {reveal_toolbar_button("examples-block", "例句")}
</div>
<div id="examples-block" class="example-block hidden">
{example_sections}
</div>
</div>
{study_script}
"""
    back = f"""
<div class="card-shell">
<div class="chapter-label">{{{{Chapter}}}}</div>
<div class="grammar-title">{{{{Word}}}}</div>
{nuance_blocks}
{grammar_blocks}
<hr class="answer-divider"/>
<div id="examples-block" class="example-block">
{example_sections}
</div>
</div>
{study_script}
"""
    field_names = [
        "Chapter",
        "WordPair",
        "Word",
        "Example1CN",
        "Example2CN",
        *_multilocale_field_names(overlay_fields),
    ]
    return genanki.Model(
        stable_id("spr-26-pku.differences.multilocale"),
        "FinalsDifferences_Multilocale",
        fields=[{"name": name} for name in field_names],
        templates=[{"name": "Difference_Card", "qfmt": front, "afmt": back}],
        css=STUDY_CSS,
    )


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
            *_multilocale_field_names(spec.overlay_fields),
        ]
        return model, field_names
    if deck_key == "jingdu-qimo-grammar":
        return build_multilocale_jingdu_grammar_model(), [
            "Chapter",
            "GrammarPoint",
            "Example1CN",
            "Example2CN",
            "Example3CN",
            *_multilocale_field_names(spec.overlay_fields),
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
            *_multilocale_field_names(spec.overlay_fields),
        ]
    return build_multilocale_differences_model(), [
        "Chapter",
        "WordPair",
        "Word",
        "Example1CN",
        "Example2CN",
        *_multilocale_field_names(spec.overlay_fields),
    ]


def _prepare_vocab_row(row: dict[str, str]) -> dict[str, str]:
    prepared = dict(row)
    prepared["Collocations"] = expand_collocations(row["Collocations"], row["Hanzi"])
    return prepared


def build_master_finals_package(
    root_deck_name: str | None = None,
    *,
    finals_dir: Path | None = None,
) -> genanki.Package:
    root_name = root_deck_name or master_deck_name()
    base_dir = finals_dir or FINALS_DIR

    deck_registry: dict[str, genanki.Deck] = {}
    models_by_id: dict[int, genanki.Model] = {}
    model_cache: dict[str, genanki.Model] = {}
    field_names_cache: dict[str, list[str]] = {}

    for course_spec in get_course_specs().values():
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
                subdeck = aspect_subdeck_name(root_name, course_label, chapter, aspect)
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


def summarize_master_package(
    *,
    finals_dir: Path | None = None,
) -> tuple[int, int, Counter[str]]:
    note_count = 0
    card_count = 0
    subdeck_counts: Counter[str] = Counter()
    base_dir = finals_dir or FINALS_DIR
    root_name = master_deck_name()

    for course_spec in get_course_specs().values():
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
                subdeck = aspect_subdeck_name(root_name, course_label, chapter, aspect)
                subdeck_counts[subdeck] += 1
                note_count += 1
                card_count += cards_per
    return note_count, card_count, subdeck_counts
