"""Parse PKU Sem 1 tab-separated word list source file."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_CEDICT_JUNK = re.compile(
    r"\[[^\]]+\]|"
    r"M:\s*[^;]+|"
    r"[^]*|"
    r"VARIANT OF[^;]+|"
    r"See also[^;]+|"
    r"abbr\. to[^;]+",
    re.IGNORECASE,
)
_WHITESPACE = re.compile(r"\s+")


@dataclass
class Sem1SourceRow:
    hanzi: str
    numbered_pinyin: str
    raw_gloss: str
    chapter: str
    source_category: str
    line_number: int
    tags: list[str] = field(default_factory=list)


def _classify_source_category(section: str) -> str:
    if "文学课" in section and "成语" in section:
        return "literature-chengyu"
    if "文学课" in section and ("专有名词" in section or "专用名词" in section):
        return "literature-proper-nouns"
    if "文学课" in section:
        return "literature-vocab"
    if "成语" in section:
        return "chengyu"
    if "专用名词" in section or "专有名词" in section:
        return "proper-nouns"
    return "vocab"


def _extract_tags(gloss: str) -> list[str]:
    tags: list[str] = []
    for match in re.finditer(
        r"\((?:idiom|loanword|pharm\.|bound form|coll\.|fig\.|lit\.|medicine|"
        r"dialect|archaic|Internet slang)\)",
        gloss,
        re.IGNORECASE,
    ):
        tags.append(match.group(0).strip("()").lower())
    for token in re.findall(
        r"\b(?:NOUN|VERB|V\.|N\.|ADJ\.|ADV\.|CONJ\.|AUX\.|ATTR\.|B\.F\.|F\.E\.|"
        r"ID\.|R\.V\.|V\.P\.|V\.O\.|S\.V\.|M\.P\.|R\.F\.|N\.PHRASE|PLUR)\b",
        gloss,
    ):
        tags.append(token.rstrip(".").lower())
    if "idiom" in gloss.lower() or "F.E." in gloss:
        tags.append("idiom")
    return tags


def clean_gloss_text(gloss: str) -> str:
    """Remove CEDICT markup while preserving example sentences."""
    cleaned = _CEDICT_JUNK.sub(" ", gloss)
    cleaned = cleaned.replace("(-//-)", " ")
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()
    return cleaned


def parse_sem1_source(source_path: Path) -> list[Sem1SourceRow]:
    """Parse the Sem 1 source file into structured rows."""
    text = source_path.read_text(encoding="utf-8-sig")
    rows: list[Sem1SourceRow] = []
    section = "uncategorized"

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("//"):
            section = line[2:].strip()
            continue
        if "\t" not in line:
            continue

        parts = line.split("\t", 2)
        hanzi = parts[0].strip()
        numbered_pinyin = parts[1].strip() if len(parts) > 1 else ""
        raw_gloss = parts[2].strip() if len(parts) > 2 else ""
        if not hanzi:
            continue

        rows.append(
            Sem1SourceRow(
                hanzi=hanzi,
                numbered_pinyin=numbered_pinyin,
                raw_gloss=raw_gloss,
                chapter=section,
                source_category=_classify_source_category(section),
                line_number=line_number,
                tags=_extract_tags(raw_gloss),
            ),
        )

    return rows
