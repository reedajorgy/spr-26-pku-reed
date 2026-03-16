#!/usr/bin/env python3
"""
Build a rich vocabulary learning CSV using the Gemini API.
Reads kouyu_vocab_ch1-9.txt, enriches each word via Gemini, and writes
a new timestamped CSV into outputs/. Never overwrites existing files.
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import google.generativeai as genai

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = PROJECT_ROOT / "kouyu_vocab_ch1-9.txt"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
BATCH_SIZE = 20
RATE_LIMIT_SECONDS = 1.5
MAX_RETRIES_PER_BATCH = 1

CSV_HEADER = [
    "chapter",
    "hanzi",
    "pinyin",
    "mandarin_意义",
    "英文意义",
    "词性",
    "搭配",
    "色彩",
    "example_sentence",
    "example_sentence_en",
    "usage_note",
    "common_errors",
    "related_words",
]

CSV_HEADER_LINE = ",".join(CSV_HEADER)

SYSTEM_INSTRUCTION = (
    "You are a Chinese vocabulary assistant. You must respond with ONLY a CSV table: no markdown, no code fences, "
    "no explanation before or after. Use commas only as CSV delimiters; if a field contains a comma or newline, "
    "wrap the entire field in double quotes. No extra lines before the header or after the last row. "
    "Output encoding is UTF-8."
)

EXAMPLE_ROW = "1,两手空空,liǎng shǒu kōngkōng,手里没有什么东西。,empty-handed; with nothing,,,他两手空空地回来了。,He came back empty-handed.,Used for having no possessions or results.,Confusing with 一无所有.,空手"


def load_vocab_from_txt(limit: int | None) -> list[dict]:
    """Parse kouyu_vocab_ch1-9.txt into list of dicts with chapter, hanzi, pinyin, definition."""
    rows = []
    with open(INPUT_PATH, "r", encoding="utf-8") as file:
        for line in file:
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
            rows.append(
                {
                    "chapter": chapter_num,
                    "hanzi": hanzi,
                    "pinyin": pinyin,
                    "definition": definition,
                },
            )
            if limit is not None and len(rows) >= limit:
                break
    return rows


def build_batch_prompt(batch: list[dict]) -> str:
    """Build the user prompt for one batch of words."""
    lines = [
        "Fill in the following vocabulary items as a CSV table.",
        "Use this exact header (first line):",
        CSV_HEADER_LINE,
        "",
        "Example of one row (same columns):",
        EXAMPLE_ROW,
        "",
        "Now output one CSV block: first line is the header above, then one row per word below.",
        "For each word provide: mandarin_意义 (Chinese definition), 英文意义 (English), 词性 (名/动/形/副/介/量/连/代/助等), 搭配 (collocations with ～), 色彩 (书面/口语/中性/贬义/褒义), example_sentence (one natural Chinese sentence), example_sentence_en (English translation), usage_note (when to use/avoid), common_errors (optional), related_words (optional).",
        "Keep chapter, hanzi, pinyin exactly as given.",
        "",
        "Words in this batch:",
    ]
    for item in batch:
        lines.append(
            f"  chapter={item['chapter']}  hanzi={item['hanzi']}  pinyin={item['pinyin']}  definition={item['definition']}",
        )
    return "\n".join(lines)


def strip_markdown_csv(text: str) -> str:
    """Remove markdown code fence around CSV if present."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[: text.rfind("```")].strip()
    return text.strip()


def parse_csv_block(block: str, expected_columns: int) -> tuple[list[dict], str | None]:
    """
    Parse a CSV block. Return (list of row dicts, None) on success,
    or ([], error_message) on failure.
    """
    block = strip_markdown_csv(block)
    if not block:
        return [], "Empty response after stripping markdown"
    reader = csv.reader(block.splitlines())
    try:
        header = next(reader)
    except StopIteration:
        return [], "No header line"
    if len(header) != expected_columns:
        return [], f"Header has {len(header)} columns, expected {expected_columns}"
    rows = []
    for row in reader:
        if len(row) == 1 and not row[0].strip():
            continue
        padded = (
            row + [""] * (expected_columns - len(row))
            if len(row) < expected_columns
            else row[:expected_columns]
        )
        rows.append(dict(zip(CSV_HEADER, padded)))
    return rows, None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build vocabulary learning CSV via Gemini (timestamped output).",
    )
    parser.add_argument("--limit", type=int, default=None, help="Process only first N words (for testing).")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("gemini_api_1")
    if not api_key:
        print("Error: gemini_api_1 not set in .env", file=sys.stderr)
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        "gemini-2.0-flash",
        system_instruction=SYSTEM_INSTRUCTION,
    )

    vocab = load_vocab_from_txt(args.limit)
    if not vocab:
        print("No vocabulary entries found.", file=sys.stderr)
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"kouyu_vocab_guide_{timestamp}.csv"

    all_rows: list[dict] = []
    failed_batches: list[tuple[int, list[dict]]] = []

    for start in range(0, len(vocab), BATCH_SIZE):
        batch = vocab[start : start + BATCH_SIZE]
        batch_index = start // BATCH_SIZE + 1
        prompt = build_batch_prompt(batch)

        for attempt in range(MAX_RETRIES_PER_BATCH + 1):
            try:
                response = model.generate_content(prompt)
                text = (
                    response.text
                    if hasattr(response, "text")
                    else (response.candidates[0].content.parts[0].text if response.candidates else "")
                )
                if not text:
                    raise ValueError("Empty model response")
            except Exception as error:
                if attempt < MAX_RETRIES_PER_BATCH:
                    time.sleep(RATE_LIMIT_SECONDS)
                    continue
                print(f"Batch {batch_index} failed after retries: {error}", file=sys.stderr)
                failed_batches.append((batch_index, batch))
                break

            rows, err = parse_csv_block(text, len(CSV_HEADER))
            if err is None and len(rows) == len(batch):
                all_rows.extend(rows)
                break
            if attempt < MAX_RETRIES_PER_BATCH:
                time.sleep(RATE_LIMIT_SECONDS)
                continue
            print(
                f"Batch {batch_index} validation failed: {err or 'row count mismatch'} (got {len(rows)} rows)",
                file=sys.stderr,
            )
            failed_batches.append((batch_index, batch))
            break

        if start + BATCH_SIZE < len(vocab):
            time.sleep(RATE_LIMIT_SECONDS)

    with open(output_path, "w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Wrote {len(all_rows)} rows to {output_path}")
    if failed_batches:
        print(f"Failed batches: {[b[0] for b in failed_batches]}", file=sys.stderr)


if __name__ == "__main__":
    main()

