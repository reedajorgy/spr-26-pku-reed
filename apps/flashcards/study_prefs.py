"""Shared study preferences, CSS, and JS for Anki cards and web preview."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.flashcards.locale_manifest import list_supported_locales, locale_label

LOCALE_STORAGE_KEY = "spr26_mother_locale"
STUDY_SETTINGS_KEY = "spr26_study_settings"
PROGRESS_STORAGE_KEY = "spr26_study_progress"
PERSISTENCE_SETTINGS_KEY = "spr26_settings_json"

CARD_STUDY_CSS_PATH = Path(__file__).resolve().parent / "static" / "card_study.css"

DEFAULT_STUDY_SETTINGS: dict[str, Any] = {
    "mother_locale": "en",
    "auto_reveal_on_answer": True,
    "settings_panel_open": False,
    "default_revealed": [],
}

# Minified anki-persistence (Simon Lammer) — front/back and clients without localStorage.
ANKI_PERSISTENCE_JS = (
    'if(void 0===window.Persistence){var _persistenceKey="github.com/SimonLammer/anki-persistence/",'
    '_defaultKey="_default";if(window.Persistence_sessionStorage=function(){var e=!1;try{'
    '"object"==typeof window.sessionStorage&&(e=!0,this.clear=function(){for(var e=0;e<sessionStorage.length;e++){'
    'var t=sessionStorage.key(e);0==t.indexOf(_persistenceKey)&&(sessionStorage.removeItem(t),e--)}},'
    'this.setItem=function(e,t){null==t&&(t=e,e=_defaultKey),sessionStorage.setItem(_persistenceKey+e,JSON.stringify(t))},'
    'this.getItem=function(e){return null==e&&(e=_defaultKey),JSON.parse(sessionStorage.getItem(_persistenceKey+e))},'
    'this.removeItem=function(e){null==e&&(e=_defaultKey),sessionStorage.removeItem(_persistenceKey+e)})}'
    'catch(e){}this.isAvailable=function(){return e}},window.Persistence_windowKey=function(e){var t=window[e],n=!1;'
    '"object"==typeof t&&(n=!0,this.clear=function(){t[_persistenceKey]={}},this.setItem=function(e,n){'
    'null==n&&(n=e,e=_defaultKey),t[_persistenceKey][e]=n},this.getItem=function(e){'
    'return null==e&&(e=_defaultKey),null==t[_persistenceKey][e]?null:t[_persistenceKey][e]},'
    'this.removeItem=function(e){null==e&&(e=_defaultKey),delete t[_persistenceKey][e]},'
    'null==t[_persistenceKey]&&this.clear()),this.isAvailable=function(){return n}},'
    'window.Persistence=new Persistence_sessionStorage,Persistence.isAvailable()||'
    '(window.Persistence=new Persistence_windowKey("py")),!Persistence.isAvailable()){'
    'var titleStartIndex=window.location.toString().indexOf("title"),'
    'titleContentIndex=window.location.toString().indexOf("main",titleStartIndex);'
    'titleStartIndex>0&&titleContentIndex>0&&titleContentIndex-titleStartIndex<10&&'
    '(window.Persistence=new Persistence_windowKey("qt"))}}'
)


def load_card_study_css() -> str:
    return CARD_STUDY_CSS_PATH.read_text(encoding="utf-8")


# Kept for imports that expect inline layout rules; prefer load_card_study_css().
STUDY_LAYOUT_CSS = ""


def build_study_js() -> str:
    settings_json = json.dumps(DEFAULT_STUDY_SETTINGS)
    latin_locales_json = json.dumps(["en", "fr", "es"])
    return f"""
var SPR26_LOCALE_KEY = "{LOCALE_STORAGE_KEY}";
var SPR26_SETTINGS_KEY = "{STUDY_SETTINGS_KEY}";
var SPR26_PERSISTENCE_KEY = "{PERSISTENCE_SETTINGS_KEY}";
var SPR26_DEFAULT_SETTINGS = {settings_json};
var SPR26_LATIN_LOCALES = {latin_locales_json};

function spr26StorageAvailable() {{
  try {{
    var probe = "__spr26_probe__";
    localStorage.setItem(probe, "1");
    localStorage.removeItem(probe);
    return true;
  }} catch (e) {{
    return false;
  }}
}}

function spr26StorageGetRaw() {{
  if (spr26StorageAvailable()) {{
    try {{
      return localStorage.getItem(SPR26_SETTINGS_KEY);
    }} catch (e) {{}}
  }}
  if (window.Persistence && Persistence.isAvailable()) {{
    try {{
      return Persistence.getItem(SPR26_PERSISTENCE_KEY);
    }} catch (e) {{}}
  }}
  return null;
}}

function spr26StorageSetRaw(serialized) {{
  if (spr26StorageAvailable()) {{
    try {{
      localStorage.setItem(SPR26_SETTINGS_KEY, serialized);
      return;
    }} catch (e) {{}}
  }}
  if (window.Persistence && Persistence.isAvailable()) {{
    try {{
      Persistence.setItem(SPR26_PERSISTENCE_KEY, serialized);
    }} catch (e) {{}}
  }}
}}

function spr26GetSettings() {{
  try {{
    var raw = spr26StorageGetRaw();
    if (!raw) {{ return Object.assign({{}}, SPR26_DEFAULT_SETTINGS); }}
    var parsed = JSON.parse(raw);
    return Object.assign({{}}, SPR26_DEFAULT_SETTINGS, parsed);
  }} catch (e) {{
    return Object.assign({{}}, SPR26_DEFAULT_SETTINGS);
  }}
}}

function spr26SaveSettings(partial) {{
  var next = Object.assign(spr26GetSettings(), partial || {{}});
  spr26StorageSetRaw(JSON.stringify(next));
  try {{
    if (next.mother_locale) {{
      localStorage.setItem(SPR26_LOCALE_KEY, next.mother_locale);
    }}
  }} catch (e) {{}}
  return next;
}}

function spr26GetLocale() {{
  var settings = spr26GetSettings();
  if (settings.mother_locale) {{ return settings.mother_locale; }}
  try {{
    if (spr26StorageAvailable()) {{
      return localStorage.getItem(SPR26_LOCALE_KEY) || "en";
    }}
  }} catch (e) {{}}
  return "en";
}}

function spr26FontClass(code) {{
  if (SPR26_LATIN_LOCALES.indexOf(code) >= 0) {{
    return "font-latin";
  }}
  return "font-script-" + code;
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
  var shells = document.querySelectorAll(".card-shell");
  var fontClass = spr26FontClass(code);
  for (var shellIndex = 0; shellIndex < shells.length; shellIndex++) {{
    var shell = shells[shellIndex];
    shell.setAttribute("lang", code);
    shell.setAttribute("data-locale", code);
    shell.className = shell.className
      .replace(/\\bfont-latin\\b/g, "")
      .replace(/\\bfont-script-[a-z]+\\b/g, "")
      .replace(/\\s+/g, " ")
      .trim();
    if (shell.className.indexOf("card-shell") < 0) {{
      shell.className = "card-shell " + fontClass;
    }} else {{
      shell.className = shell.className + " " + fontClass;
    }}
  }}
}}

function spr26SetLocale(code) {{
  spr26SaveSettings({{ mother_locale: code }});
  spr26ApplyLocale(code);
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
  if (settings.auto_reveal_on_answer !== false) {{
    spr26RevealBlock("examples-block");
  }}
}}

function spr26BindSettingsPanel() {{
  var panel = document.querySelector(".settings-panel");
  if (panel && !panel.getAttribute("data-spr26-bound")) {{
    panel.setAttribute("data-spr26-bound", "1");
    panel.addEventListener("toggle", function() {{
      spr26SaveSettings({{ settings_panel_open: panel.open }});
    }});
  }}
  var autoReveal = document.getElementById("spr26-auto-reveal");
  if (autoReveal && !autoReveal.getAttribute("data-spr26-bound")) {{
    autoReveal.setAttribute("data-spr26-bound", "1");
    autoReveal.addEventListener("change", function() {{
      spr26SaveSettings({{ auto_reveal_on_answer: autoReveal.checked }});
    }});
  }}
  var selectors = document.querySelectorAll(".spr26-locale-select");
  for (var index = 0; index < selectors.length; index++) {{
    var select = selectors[index];
    if (!select.getAttribute("data-spr26-bound")) {{
      select.setAttribute("data-spr26-bound", "1");
      select.addEventListener("change", function(event) {{
        spr26SetLocale(event.target.value);
      }});
    }}
  }}
}}

function spr26Bootstrap() {{
  var settings = spr26GetSettings();
  var panel = document.querySelector(".settings-panel");
  if (panel && settings.settings_panel_open) {{
    panel.open = true;
  }}
  var autoReveal = document.getElementById("spr26-auto-reveal");
  if (autoReveal) {{
    autoReveal.checked = settings.auto_reveal_on_answer !== false;
  }}
  spr26ApplyLocale(spr26GetLocale());
  spr26BindSettingsPanel();
}}

document.addEventListener("DOMContentLoaded", spr26Bootstrap);
"""


def locale_selector_html() -> str:
    options = []
    for locale_code in list_supported_locales():
        label = locale_label(locale_code)
        options.append(f'<option value="{locale_code}">{label}</option>')
    option_html = "\n".join(options)
    return f"""
<details class="settings-panel">
  <summary>Study settings</summary>
  <div class="settings-panel-body">
    <div class="locale-row">
      <label for="spr26-locale-select">Mother language</label>
      <select id="spr26-locale-select" class="spr26-locale-select">
{option_html}
      </select>
    </div>
    <div class="settings-checkbox-row">
      <label>
        <input type="checkbox" id="spr26-auto-reveal" checked />
        Reveal examples when showing answer
      </label>
    </div>
  </div>
</details>
"""


def persistence_script_tag() -> str:
    return f"<script>\n{ANKI_PERSISTENCE_JS}\n</script>"


def bootstrap_script_tag() -> str:
    return "<script>spr26Bootstrap();</script>"


def study_script_tag() -> str:
    return (
        f"{persistence_script_tag()}\n"
        f"<script>\n{build_study_js()}\n</script>\n"
        f"{bootstrap_script_tag()}"
    )


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
