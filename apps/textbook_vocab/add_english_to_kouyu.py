#!/usr/bin/env python3
"""
Append a short English translation (one phrase) to each line of kouyu_vocab_ch1-9.txt.
Uses Gemini in batches to generate the English column, then rewrites the file.
"""

import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
import google.generativeai as genai

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = PROJECT_ROOT / "outputs" / "kouyu_vocab_ch1-9.txt"
BATCH_SIZE = 35
RATE_LIMIT_SECONDS = 1.0


def load_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def parse_line(line: str) -> tuple[str, str, str] | None:
    """Return (chapter_and_num, hanzi, rest) or None if not a data line."""
    line = line.strip()
    if not line:
        return None
    parts = line.split("\t")
    if len(parts) < 5:
        return None
    chapter_num = parts[0].strip()
    hanzi = parts[2].strip()
    rest = parts[4].strip()
    return (chapter_num, hanzi, rest)


def build_batch_prompt(lines: list[str], start: int, end: int) -> str:
    batch_lines = lines[start:end]
    prompt_parts = [
        "You are a Chinese–English vocabulary assistant.",
        "Below are lines from a vocab file. Each line has: chapter, index, hanzi, pinyin, Chinese definition.",
        "Output ONLY a list of English translations: one short phrase per line, in the same order.",
        "Each phrase should be the standard English meaning of the VOCAB WORD (the hanzi), e.g. empty-handed, resume, real estate.",
        "Output exactly N lines, no numbering, no bullets, no other text. One English phrase per line.",
        "",
        f"Number of lines to translate: {len(batch_lines)}",
        "",
        "Lines:",
    ]
    for line in batch_lines:
        prompt_parts.append(line)
    return "\n".join(prompt_parts)


def parse_english_response(text: str, expected_count: int) -> list[str]:
    """Extract one English phrase per line from model output."""
    text = text.strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    result = []
    for line in lines:
        if len(result) >= expected_count:
            break
        line = re.sub(r"^[\d\.\-\*]+\s*", "", line).strip()
        if line:
            result.append(line)
    return result[:expected_count]


def main() -> None:
    load_dotenv()
    api_key = os.environ.get("gemini_api_1")
    if not api_key:
        print("Error: gemini_api_1 not set in .env", file=sys.stderr)
        sys.exit(1)

    if not INPUT_PATH.is_file():
        print(f"Error: input file not found: {INPUT_PATH}", file=sys.stderr)
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    lines = load_lines(INPUT_PATH)
    english_phrases: list[str] = []
    data_line_count = 0
    for line in lines:
        if parse_line(line) is not None:
            data_line_count += 1

    for start in range(0, len(lines), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(lines))
        batch = [line for line in lines[start:end] if parse_line(line) is not None]
        if not batch:
            for _ in range(start, end):
                english_phrases.append("")
            continue

        prompt = build_batch_prompt(lines, start, end)
        response = model.generate_content(prompt)
        response_text = response.text if response.text else ""
        parsed = parse_english_response(response_text, len(batch))

        for idx in range(end - start):
            if parse_line(lines[start + idx]) is not None:
                english_phrases.append(parsed.pop(0) if parsed else "")
            else:
                english_phrases.append("")

        if end % 50 == 0 or end == len(lines):
            print(f"Processed {end}/{len(lines)} lines...", file=sys.stderr)
        time.sleep(RATE_LIMIT_SECONDS)

    if len(english_phrases) != len(lines):
        print(
            f"Error: got {len(english_phrases)} English phrases for {len(lines)} lines",
            file=sys.stderr,
        )
        sys.exit(1)

    out_lines = []
    for i, line in enumerate(lines):
        stripped = line.rstrip("\n")
        if parse_line(line) is not None and i < len(english_phrases):
            out_lines.append(stripped + "\t" + (english_phrases[i] or ""))
        else:
            out_lines.append(stripped)
    INPUT_PATH.write_text("\n".join(out_lines) + ("\n" if lines else ""), encoding="utf-8")
    count = sum(1 for line in lines if parse_line(line) is not None)
    print(f"Wrote {INPUT_PATH} with English column ({count} entries).", file=sys.stderr)


if __name__ == "__main__":
    main()
