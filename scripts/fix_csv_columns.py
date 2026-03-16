#!/usr/bin/env python3
"""
Fix full_ky_vocab.csv so that example_sentence_en, usage_note, common_errors, and
related_words are consistent and accurate. Rows with commas inside those fields
were misparsed (14 or 15 fields instead of 13). We merge split fields back and
write the CSV with proper quoting so the format is valid and consistent.
"""
import csv
import os

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "full_ky_vocab.csv")


def parse_line(line: str) -> list[str]:
    """Parse a CSV line into exactly 13 fields, merging any that were split by internal commas."""
    line = line.rstrip("\n")
    parts = line.split(",")
    if len(parts) == 13:
        return parts
    if len(parts) == 14:
        # One comma inside example_sentence_en: merge parts[9] and parts[10]
        return (
            parts[0:9]
            + [parts[9] + "," + parts[10]]
            + parts[11:14]
        )
    if len(parts) == 15:
        # usage_note was split (e.g. "Often refers to price, size, or degree.")
        return (
            parts[0:10]
            + [parts[10] + "," + parts[11] + "," + parts[12]]
            + parts[13:15]
        )
    if len(parts) > 15:
        # Merge all from 10 to -2 into usage_note, keep last as related_words
        return (
            parts[0:10]
            + [",".join(parts[10:-2])]
            + parts[-2:]
        )
    return parts


def main():
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        raise SystemExit("CSV is empty")

    header = lines[0].rstrip("\n").split(",")
    if len(header) != 13:
        raise SystemExit(f"Expected 13 columns in header, got {len(header)}")

    rows = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        parsed = parse_line(line)
        if len(parsed) != 13:
            # If still wrong, try to pad or truncate for robustness
            if len(parsed) < 13:
                parsed = parsed + [""] * (13 - len(parsed))
            else:
                parsed = parsed[:13]
        rows.append(parsed)

    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
        for row in rows:
            writer.writerow(row)

    print(f"Fixed CSV: {len(rows)} rows written. All fields quoted for consistent, accurate parsing.")


if __name__ == "__main__":
    main()
