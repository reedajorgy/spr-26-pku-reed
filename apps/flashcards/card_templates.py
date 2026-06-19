"""Anki note type HTML templates aligned with the web study card."""

from __future__ import annotations

import genanki

from apps.flashcards.anki_build import stable_id
from apps.flashcards.locale_manifest import list_supported_locales
from apps.flashcards.study_prefs import (
    bootstrap_script_tag,
    locale_selector_html,
    load_card_study_css,
    reveal_toolbar_button,
    study_script_tag,
)

STUDY_CSS = load_card_study_css()


def _locale_blocks_html(field_prefix: str, inner_html: str) -> str:
    blocks = []
    for locale_code in list_supported_locales():
        field_name = f"{field_prefix}_{locale_code}"
        blocks.append(
            f'<div class="locale-block text-mother" data-locale="{locale_code}">'
            f"{inner_html.replace('FIELD', '{{' + field_name + '}}')}"
            f"</div>",
        )
    return "\n".join(blocks)


def _title_base_from_overlay(overlay_field: str) -> str:
    return "".join(part.capitalize() for part in overlay_field.split("_"))


def multilocale_field_names(overlay_fields: list[str]) -> list[str]:
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
            f'<div class="locale-block text-mother" data-locale="{locale_code}">'
            f'<div class="meta-line text-mother">{{{{ExampleEn_{locale_code}}}}}</div></div>',
        )
    return "\n".join(blocks)


def _vocab_usage_blocks() -> str:
    blocks = []
    for locale_code in list_supported_locales():
        blocks.append(
            f"{{{{#UsageNote_{locale_code}}}}}"
            f'<div class="locale-block text-mother" data-locale="{locale_code}">'
            f'<div class="meta-line text-mother"><span class="meta-label">用法</span> '
            f"{{{{UsageNote_{locale_code}}}}}</div></div>"
            f"{{{{/UsageNote_{locale_code}}}}}",
        )
    return "\n".join(blocks)


def _vocab_meta_front() -> str:
    return """
<div class="meta-footer">
  <div class="badges">{{{{POS}}}} · {{{{Color}}}}</div>
  <div class="meta-line text-zh"><span class="meta-label">搭配</span> {{{{Collocations}}}}</div>
</div>
"""


def _vocab_example_block() -> str:
    return f"""
<div id="example-block" class="example-block hidden">
  <div class="meta-line text-zh"><span class="meta-label">例句</span> {{{{ExampleCN}}}}</div>
  {_vocab_example_en_blocks()}
  {_vocab_usage_blocks()}
  {{{{#CommonErrors}}}}
  <div class="meta-line text-mother"><span class="meta-label">易错</span> {{{{CommonErrors}}}}</div>
  {{{{/CommonErrors}}}}
  {{{{#RelatedWords}}}}
  <div class="meta-line text-zh"><span class="meta-label">相关</span> {{{{RelatedWords}}}}</div>
  {{{{/RelatedWords}}}}
</div>
"""


def _vocab_meta_back_visible() -> str:
    return f"""
<div class="meta-footer">
  <div class="badges">{{{{POS}}}} · {{{{Color}}}}</div>
  <div class="meta-line text-zh"><span class="meta-label">搭配</span> {{{{Collocations}}}}</div>
</div>
<div id="example-block" class="example-block">
  <div class="meta-line text-zh"><span class="meta-label">例句</span> {{{{ExampleCN}}}}</div>
  {_vocab_example_en_blocks()}
  {_vocab_usage_blocks()}
  {{{{#CommonErrors}}}}
  <div class="meta-line text-mother"><span class="meta-label">易错</span> {{{{CommonErrors}}}}</div>
  {{{{/CommonErrors}}}}
  {{{{#RelatedWords}}}}
  <div class="meta-line text-zh"><span class="meta-label">相关</span> {{{{RelatedWords}}}}</div>
  {{{{/RelatedWords}}}}
</div>
"""


def _vocab_toggle_toolbar() -> str:
    return f"""
<div class="card-toolbar">
  {reveal_toolbar_button("hanzi-block", "汉字")}
  {reveal_toolbar_button("pinyin-block", "拼音")}
  {reveal_toolbar_button("translation-block", "Definition")}
  {reveal_toolbar_button("example-block", "例句")}
</div>
"""


def _card_opening() -> str:
    return f"""
<div class="card-shell font-latin">
<div class="chapter-label">{{{{Chapter}}}}</div>
{locale_selector_html()}
"""


def _vocab_answer_panel() -> str:
    return """
<div class="answer-panel">
  <div class="hanzi-text text-zh">{{{{Hanzi}}}}</div>
  <div class="pinyin-text text-latin">{{{{Pinyin}}}}</div>
</div>
"""


def build_multilocale_vocab_model() -> genanki.Model:
    overlay_fields = ["meaning", "example_en", "usage_note"]
    meaning_blocks = _locale_blocks_html(
        "Meaning",
        '<div class="translation-text text-mother">FIELD</div>',
    )
    study_script = study_script_tag()
    toggle_front = f"""
{_card_opening()}
<div class="prompt">Reveal hints as needed, then grade yourself.</div>
{_vocab_toggle_toolbar()}
<div id="hanzi-block" class="reveal-block hidden">
  <div class="hanzi-text text-zh">{{{{Hanzi}}}}</div>
</div>
<div id="pinyin-block" class="reveal-block hidden">
  <div class="pinyin-text text-latin">{{{{Pinyin}}}}</div>
</div>
<div id="translation-block" class="reveal-block hidden">
  {meaning_blocks}
  <div class="mandarin-def text-zh">{{{{MandarinDef}}}}</div>
</div>
{_vocab_meta_front()}
{_vocab_example_block()}
</div>
{study_script}
"""
    toggle_back = f"""
{{{{FrontSide}}}}
<hr class="answer-divider"/>
{_vocab_answer_panel()}
<script>spr26RevealOnBack();</script>
{bootstrap_script_tag()}
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
<div class="card-shell font-latin">
<div class="chapter-label">{{{{Chapter}}}}</div>
<div class="hanzi-text text-zh">{{{{Hanzi}}}}</div>
<div class="pinyin-text text-latin">{{{{Pinyin}}}}</div>
<div class="mandarin-def text-zh">{{{{MandarinDef}}}}</div>
{_vocab_meta_back_visible()}
</div>
{study_script}
{bootstrap_script_tag()}
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
        *multilocale_field_names(overlay_fields),
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
                f'<div class="locale-block text-mother" data-locale="{locale_code}">'
                f"{block_inner}</div>",
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
                f'<div class="locale-block text-mother" data-locale="{locale_code}">'
                f'<div class="meta-line text-mother">{{{{{title_base}_{locale_code}}}}}</div></div>',
            )
        example_sections += f"""
<div class="meta-line text-zh"><span class="meta-label">例{example_index}</span> {{{{{cn_field}}}}}</div>
{"".join(en_blocks)}
"""
    return example_sections


def build_multilocale_jingdu_grammar_model() -> genanki.Model:
    overlay_fields = ["use_case", "example_1_en", "example_2_en", "example_3_en"]
    use_case_blocks = _grammar_locale_body(
        overlay_fields[:1],
        '<div class="body-text text-mother">FIELD</div>',
    )
    example_sections = _jingdu_grammar_example_sections()
    study_script = study_script_tag()
    front = f"""
{_card_opening()}
<div class="grammar-title text-zh">{{{{GrammarPoint}}}}</div>
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
{{{{FrontSide}}}}
<hr class="answer-divider"/>
<script>spr26RevealOnBack();</script>
{bootstrap_script_tag()}
"""
    field_names = [
        "Chapter",
        "GrammarPoint",
        "Example1CN",
        "Example2CN",
        "Example3CN",
        *multilocale_field_names(overlay_fields),
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
        '<div class="body-text text-mother">FIELD</div>',
    )
    kouyu_examples = """
<div class="meta-line text-zh">{{Example1}}</div>
<div class="meta-line text-zh">{{Example2}}</div>
<div class="meta-line text-zh">{{Example3}}</div>
<div class="meta-line text-zh">{{Example4}}</div>
<div class="meta-line text-zh">{{Example5}}</div>
"""
    study_script = study_script_tag()
    front = f"""
{_card_opening()}
<div class="grammar-title text-zh">{{{{Pattern}}}}</div>
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
{{{{FrontSide}}}}
<hr class="answer-divider"/>
<script>spr26RevealOnBack();</script>
{bootstrap_script_tag()}
"""
    field_names = [
        "Chapter",
        "Pattern",
        "Example1",
        "Example2",
        "Example3",
        "Example4",
        "Example5",
        *multilocale_field_names(overlay_fields),
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
        '<div class="body-text text-mother">FIELD</div>',
    )
    grammar_blocks = _grammar_locale_body(
        ["grammar_notes"],
        '<div class="body-text text-mother"><b>Grammar:</b> FIELD</div>',
    )
    example_sections = ""
    for example_index in range(1, 3):
        cn_field = f"Example{example_index}CN"
        en_overlay = f"example_{example_index}_en"
        title_base = _title_base_from_overlay(en_overlay)
        en_blocks = []
        for locale_code in list_supported_locales():
            en_blocks.append(
                f'<div class="locale-block text-mother" data-locale="{locale_code}">'
                f'<div class="meta-line text-mother">{{{{{title_base}_{locale_code}}}}}</div></div>',
            )
        example_sections += f"""
<div class="meta-line text-zh">{{{{{cn_field}}}}}</div>
{"".join(en_blocks)}
"""
    study_script = study_script_tag()
    front = f"""
{_card_opening()}
<div class="grammar-title text-zh">{{{{Word}}}} <span class="pair-label">({{{{WordPair}}}})</span></div>
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
{{{{FrontSide}}}}
<hr class="answer-divider"/>
<div class="grammar-body-back text-mother">{grammar_blocks}</div>
<script>spr26RevealOnBack();</script>
{bootstrap_script_tag()}
"""
    field_names = [
        "Chapter",
        "WordPair",
        "Word",
        "Example1CN",
        "Example2CN",
        *multilocale_field_names(overlay_fields),
    ]
    return genanki.Model(
        stable_id("spr-26-pku.differences.multilocale"),
        "FinalsDifferences_Multilocale",
        fields=[{"name": name} for name in field_names],
        templates=[{"name": "Difference_Card", "qfmt": front, "afmt": back}],
        css=STUDY_CSS,
    )
