"""Shared study preferences, CSS, and JS for Anki cards and web preview."""

from __future__ import annotations

import json
from typing import Any

from apps.flashcards.locale_manifest import list_supported_locales, locale_label

LOCALE_STORAGE_KEY = "spr26_mother_locale"
STUDY_SETTINGS_KEY = "spr26_study_settings"
PROGRESS_STORAGE_KEY = "spr26_study_progress"

DEFAULT_STUDY_SETTINGS: dict[str, Any] = {
    "mother_locale": "en",
    "auto_reveal_on_answer": True,
    "default_revealed": [],
}


STUDY_LAYOUT_CSS = """
.card-shell {
  max-width: 42rem;
  margin: 0 auto;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}
.settings-panel {
  margin: 0 0 12px;
  border: 1px solid #d8d8d8;
  border-radius: 8px;
  background: #fff;
}
.settings-panel summary {
  cursor: pointer;
  padding: 8px 12px;
  font-size: 13px;
  color: #444;
  list-style: none;
  user-select: none;
}
.settings-panel summary::-webkit-details-marker { display: none; }
.settings-panel[open] summary { border-bottom: 1px solid #e8e8e8; }
.settings-panel-body {
  padding: 10px 12px 12px;
}
.locale-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.locale-row label {
  font-size: 13px;
  color: #555;
}
.spr26-locale-select {
  font-size: 14px;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid #888;
  min-width: 10rem;
}
.locale-block { display: none; }
.locale-block.active { display: block; }
.card-toolbar,
.toggle-row {
  margin: 12px 0 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.toggle-btn {
  font-size: 14px;
  padding: 8px 14px;
  border: 1px solid #888;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  min-height: 2.5rem;
}
.toggle-btn:hover { background: #f3f3f3; }
.toggle-btn:focus-visible {
  outline: 2px solid #2c5f8a;
  outline-offset: 2px;
}
.toggle-btn.is-revealed {
  background: #e8f0f8;
  border-color: #2c5f8a;
  color: #1a3d5c;
}
.reveal-block,
.example-block {
  margin: 10px 0;
  padding: 12px 14px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e0e0e0;
}
.card-body { margin-top: 4px; }
.hidden { display: none !important; }
.answer-divider {
  margin: 16px 0;
  border: none;
  border-top: 1px solid #ccc;
}
"""


def build_study_js() -> str:
    settings_json = json.dumps(DEFAULT_STUDY_SETTINGS)
    return f"""
var SPR26_LOCALE_KEY = "{LOCALE_STORAGE_KEY}";
var SPR26_SETTINGS_KEY = "{STUDY_SETTINGS_KEY}";
var SPR26_DEFAULT_SETTINGS = {settings_json};

function spr26GetSettings() {{
  try {{
    var raw = localStorage.getItem(SPR26_SETTINGS_KEY);
    if (!raw) {{ return Object.assign({{}}, SPR26_DEFAULT_SETTINGS); }}
    var parsed = JSON.parse(raw);
    return Object.assign({{}}, SPR26_DEFAULT_SETTINGS, parsed);
  }} catch (e) {{
    return Object.assign({{}}, SPR26_DEFAULT_SETTINGS);
  }}
}}

function spr26SaveSettings(partial) {{
  var next = Object.assign(spr26GetSettings(), partial || {{}});
  try {{ localStorage.setItem(SPR26_SETTINGS_KEY, JSON.stringify(next)); }} catch (e) {{}}
  return next;
}}

function spr26GetLocale() {{
  var settings = spr26GetSettings();
  if (settings.mother_locale) {{ return settings.mother_locale; }}
  try {{ return localStorage.getItem(SPR26_LOCALE_KEY) || "en"; }} catch (e) {{ return "en"; }}
}}

function spr26SetLocale(code) {{
  try {{ localStorage.setItem(SPR26_LOCALE_KEY, code); }} catch (e) {{}}
  spr26SaveSettings({{ mother_locale: code }});
  spr26ApplyLocale(code);
}}

function spr26ApplyLocale(code) {{
  var blocks = document.querySelectorAll(".locale-block");
  for (var index = 0; index < blocks.length; index++) {{
    var block = blocks[index];
    if (block.getAttribute("data-locale") === code) {{
      block.classList.add("active");
    }} else {{
      block.classList.remove("active");
    }}
  }}
  var selectors = document.querySelectorAll(".spr26-locale-select");
  for (var selectIndex = 0; selectIndex < selectors.length; selectIndex++) {{
    selectors[selectIndex].value = code;
  }}
}}

function spr26InitLocale() {{
  spr26ApplyLocale(spr26GetLocale());
}}

function toggleBlock(blockId, buttonElement) {{
  var element = document.getElementById(blockId);
  if (!element) {{ return; }}
  element.classList.toggle("hidden");
  var revealed = !element.classList.contains("hidden");
  if (buttonElement) {{
    if (revealed) {{
      buttonElement.classList.add("is-revealed");
    }} else {{
      buttonElement.classList.remove("is-revealed");
    }}
  }}
}}

function spr26RevealBlock(blockId) {{
  var element = document.getElementById(blockId);
  if (!element) {{ return; }}
  element.classList.remove("hidden");
  var button = document.querySelector('[data-reveal-target="' + blockId + '"]');
  if (button) {{ button.classList.add("is-revealed"); }}
}}

function spr26RevealOnBack() {{
  var settings = spr26GetSettings();
  spr26RevealBlock("example-block");
  if (settings.auto_reveal_on_answer) {{
    spr26RevealBlock("examples-block");
  }}
}}

document.addEventListener("DOMContentLoaded", spr26InitLocale);
"""


def locale_selector_html() -> str:
    options = []
    for locale_code in list_supported_locales():
        label = locale_label(locale_code)
        options.append(f'<option value="{locale_code}">{label}</option>')
    option_html = "\n".join(options)
    return f"""
<details class="settings-panel">
  <summary>⚙ Study settings</summary>
  <div class="settings-panel-body">
    <div class="locale-row">
      <label>Mother language</label>
      <select class="spr26-locale-select" onchange="spr26SetLocale(this.value)">
{option_html}
      </select>
    </div>
  </div>
</details>
"""


def study_script_tag() -> str:
    return f"<script>\n{build_study_js()}\n</script>"


def reveal_toolbar_button(block_id: str, label: str) -> str:
    return (
        f'<button class="toggle-btn" type="button" data-reveal-target="{block_id}" '
        f"onclick=\"toggleBlock('{block_id}', this)\">{label}</button>"
    )


def study_prefs_api_payload() -> dict[str, Any]:
    return {
        "locale_storage_key": LOCALE_STORAGE_KEY,
        "study_settings_key": STUDY_SETTINGS_KEY,
        "progress_storage_key": PROGRESS_STORAGE_KEY,
        "defaults": DEFAULT_STUDY_SETTINGS,
        "aspect_labels": {
            "Vocab": "Vocabulary",
            "Grammar": "Grammar",
            "Word_Differences": "Word differences",
        },
        "locales": [
            {"code": code, "label": locale_label(code)}
            for code in list_supported_locales()
        ],
    }
