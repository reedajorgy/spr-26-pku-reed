#!/usr/bin/env python3
"""Build vocabulary CSV from kouyu_vocab_ch1-9.txt with chapter, hanzi, pinyin, 意义, 英文, 词性, 搭配, 色彩."""

import csv
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = PROJECT_ROOT / "kouyu_vocab_ch1-9.txt"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "kouyu_vocab_ch1-9_guide.csv"

# Common 词性 tags in the source
POS_PATTERN = re.compile(r"^[（(](名|动|形|副|介|量|连|代|助)[）)]\s*")
# Trailing English: word or phrase at end after 。 or space (e.g. "customer", "resume")
ENGLISH_AT_END = re.compile(r"[。\s]+([a-zA-Z][a-zA-Z\s\-\.]*)$")
# English at start of definition (after POS): e.g. "to loan; " or "IV drip"
ENGLISH_AT_START = re.compile(r"^([a-zA-Z][a-zA-Z\s\-\.]*(?:\s*;\s*)?)\s*")


def extract_pos(definition: str) -> tuple[str, str]:
    """Return (pos, rest_of_definition)."""
    match = POS_PATTERN.match(definition)
    if match:
        pos = match.group(1)
        rest = definition[match.end() :].strip()
        return pos, rest
    return "", definition


def extract_english(definition: str) -> tuple[str, str]:
    """Return (english, definition_without_english)."""
    english = ""
    rest = definition
    match_end = ENGLISH_AT_END.search(definition)
    if match_end:
        cand = match_end.group(1).strip().rstrip(";")
        if 1 <= len(cand.split()) <= 5 and len(cand) < 80:
            english = cand
            rest = definition[: match_end.start()].strip()
            if rest.endswith("。"):
                rest = rest[:-1].strip()
    if not english:
        match_start = ENGLISH_AT_START.match(rest)
        if match_start:
            cand = match_start.group(1).strip().rstrip(";")
            if cand and 1 <= len(cand.split()) <= 5 and len(cand) < 60:
                rest_after = rest[match_start.end() :].strip()
                if any("\u4e00" <= c <= "\u9fff" for c in rest_after):
                    english = cand
                    rest = rest_after
    return english, rest


def extract_collocations(definition: str) -> str:
    """Extract 搭配 (example phrases with ～ or ｜). Meaning text is left unchanged."""
    collos = []
    for part in re.split(r"[。；]", definition):
        part = part.strip()
        if part and ("｜" in part or "～" in part):
            collos.append(part)
    return "；".join(collos) if collos else ""


def main() -> None:
    rows = []
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            chapter_label = parts[0]
            chapter_num = chapter_label.replace("chapter", "").strip()
            hanzi = parts[2]
            pinyin = parts[3]
            definition = parts[4].strip()

            pos, rest = extract_pos(definition)
            english, rest = extract_english(rest)
            collocations = extract_collocations(rest)
            mandarin_meaning = rest

            color = ""

            rows.append(
                {
                    "chapter": chapter_num,
                    "hanzi": hanzi,
                    "pinyin": pinyin,
                    "mandarin_意义": mandarin_meaning,
                    "英文意义": english,
                    "词性": pos,
                    "搭配": collocations,
                    "色彩": color,
                },
            )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(
            out,
            fieldnames=["chapter", "hanzi", "pinyin", "mandarin_意义", "英文意义", "词性", "搭配", "色彩"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

