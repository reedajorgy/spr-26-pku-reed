import re
import subprocess
from pathlib import Path


VOCAB_PAGES_BY_CHAPTER = {
    1: [4, 5],
}


def run_tesseract_on_image(image_path: Path) -> str:
    process = subprocess.run(
        [
            "tesseract",
            str(image_path),
            "stdout",
            "-l",
            "chi_sim+eng",
            "--psm",
            "4",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return process.stdout


def parse_vocab_lines(ocr_text: str):
    entries = []
    line_pattern = re.compile(
        r"^\s*(\d+)\s+(\S+)\s+([a-zA-Zāēīōūǖáéíóúǘǎěǐǒǔǚàèìòùǜü\s]+?)\s+(.+)$",
    )

    for raw_line in ocr_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = line_pattern.match(line)
        if not match:
            continue
        index_str, hanzi, pinyin, definition = match.groups()
        try:
            index = int(index_str)
        except ValueError:
            continue
        entries.append(
            {
                "index": index,
                "hanzi": hanzi,
                "pinyin": " ".join(pinyin.split()),
                "definition": definition.strip(),
            },
        )
    return entries


def format_entry(entry, chapter: int) -> str:
    return (
        f"chapter {chapter}\t"
        f"{entry['index']}\t"
        f"{entry['hanzi']}\t"
        f"{entry['pinyin']}\t"
        f"{entry['definition']}"
    )


def extract_all_vocab():
    project_root = Path(__file__).resolve().parents[2]
    kouyu_dir = project_root / "raw_materials" / "textbooks" / "kouyu"
    output_lines = []

    for chapter, pages in VOCAB_PAGES_BY_CHAPTER.items():
        for page in pages:
            image_name = f"11111_page-{page:02d}.png"
            image_path = kouyu_dir / image_name
            if not image_path.exists():
                continue
            ocr_text = run_tesseract_on_image(image_path)
            entries = parse_vocab_lines(ocr_text)
            for entry in entries:
                output_lines.append(format_entry(entry, chapter))

    output_path = project_root / "kouyu_vocab_ch1-9.txt"
    output_text = "\n".join(output_lines)
    output_path.write_text(output_text, encoding="utf-8")


if __name__ == "__main__":
    extract_all_vocab()

