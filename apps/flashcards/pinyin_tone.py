"""Convert numbered pinyin (yi2qing2yang3xing4) to tone-marked pinyin."""

from __future__ import annotations

import re

_TONE_VOWELS = {
    "a": ("ā", "á", "ǎ", "à", "a"),
    "e": ("ē", "é", "ě", "è", "e"),
    "i": ("ī", "í", "ǐ", "ì", "i"),
    "o": ("ō", "ó", "ǒ", "ò", "o"),
    "u": ("ū", "ú", "ǔ", "ù", "u"),
    "v": ("ǖ", "ǘ", "ǚ", "ǜ", "ü"),
}

_SYLLABLE_PATTERN = re.compile(
    r"(?:zh|ch|sh|[bpmfdtnlgkhjqxrzcsyw])?"
    r"(?:uang|ueng|iong|iang|ing|iao|ian|uai|uei|uen|ong|ang|eng|ai|ei|ao|ou|"
    r"an|en|in|un|uo|ua|ue|iu|ie|ia|ui|a|e|i|o|u|v)"
    r"(?:ng|n)?[1-5](?:r5)?",
    re.IGNORECASE,
)

_CHINESE_CHAR = re.compile(r"[\u4e00-\u9fff]")


def _normalize_syllable_token(token: str) -> str:
    return token.strip().lower().replace("u:", "v").replace("ü", "v")


def _apply_tone_to_syllable(syllable: str) -> str:
    normalized = _normalize_syllable_token(syllable)
    if not normalized:
        return syllable

    erhua = False
    if normalized.endswith("r5"):
        erhua = True
        normalized = normalized[:-2]

    tone_digit = normalized[-1]
    if tone_digit not in "12345":
        return syllable

    tone_index = int(tone_digit) - 1 if tone_digit != "5" else 4
    body = normalized[:-1]

    if "v" in body:
        vowel = "v"
        position = body.index("v")
    elif "a" in body:
        vowel = "a"
        position = body.index("a")
    elif "e" in body:
        vowel = "e"
        position = body.index("e")
    elif "ou" in body:
        vowel = "o"
        position = body.index("o")
    else:
        for index in range(len(body) - 1, -1, -1):
            if body[index] in "iou":
                vowel = body[index]
                position = index
                break
        else:
            return syllable

    marked_vowel = _TONE_VOWELS[vowel][tone_index]
    marked_body = body[:position] + marked_vowel + body[position + 1 :]
    marked_body = marked_body.replace("v", "ü")

    if erhua and not marked_body.endswith("r"):
        marked_body += "r"

    return marked_body


def split_numbered_syllables(text: str) -> list[str]:
    """Split a numbered-pinyin string into individual syllable tokens."""
    cleaned = text.replace("//", " ").strip()
    if not cleaned:
        return []

    syllables: list[str] = []
    for chunk in cleaned.split():
        if _CHINESE_CHAR.search(chunk):
            continue
        if re.search(r"[1-5]", chunk):
            found = _SYLLABLE_PATTERN.findall(chunk)
            if found:
                syllables.extend(found)
            else:
                syllables.append(chunk)
        else:
            syllables.append(chunk)
    return syllables


def _mark_chunk(chunk: str) -> str:
    cleaned = chunk.strip()
    if not cleaned:
        return cleaned
    if " " in cleaned:
        return " ".join(_mark_chunk(word) for word in cleaned.split())

    syllables = split_numbered_syllables(cleaned)
    if not syllables:
        return cleaned
    marked = [_apply_tone_to_syllable(syllable) for syllable in syllables]
    return "".join(marked)


def numbered_pinyin_to_tone_marks(text: str) -> str:
    """Convert numbered pinyin to tone-marked pinyin."""
    if not text or not text.strip():
        return text

    if "//" in text:
        return " ".join(_mark_chunk(chunk) for chunk in text.split("//"))

    return _mark_chunk(text)


def numbered_pinyin_for_hanzi(hanzi: str, numbered_pinyin: str) -> str:
    """Convert numbered pinyin, joining syllables for multi-character words."""
    marked = numbered_pinyin_to_tone_marks(numbered_pinyin)
    syllables = marked.split()
    if not syllables:
        return marked

    hanzi_chars = [character for character in hanzi if _CHINESE_CHAR.match(character)]
    if len(hanzi_chars) == len(syllables):
        return "".join(
            f"{character} ({syllable})" if len(hanzi_chars) > 1 else syllable
            for character, syllable in zip(hanzi_chars, syllables, strict=True)
        )
    return marked
