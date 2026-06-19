"""Lightweight CC-CEDICT loader for gap-filling Sem 1 definitions."""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

from apps.flashcards.paths import REPO_ROOT

CEDICT_URL = (
    "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz"
)
CEDICT_PATH = REPO_ROOT / "data" / "cedict_ts.u8"

_ENTRY_RE = re.compile(
    r"^(?P<traditional>\S+)\s+(?P<simplified>\S+)\s+\[(?P<pinyin>[^\]]+)\]\s+"
    r"(?P<defs>/.*?/)$",
)


class CedictLookup:
    def __init__(self, entries: dict[str, tuple[str, list[str]]]) -> None:
        self._entries = entries

    @classmethod
    def load(cls, path: Path | None = None) -> CedictLookup:
        dictionary_path = path or CEDICT_PATH
        if not dictionary_path.exists():
            raise FileNotFoundError(
                f"CC-CEDICT not found at {dictionary_path}. "
                "Run fetch_cedict() or export_sem1_csv.py --fetch-cedict.",
            )
        entries: dict[str, tuple[str, list[str]]] = {}
        with dictionary_path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("#") or not line.strip():
                    continue
                match = _ENTRY_RE.match(line.strip())
                if not match:
                    continue
                simplified = match.group("simplified")
                pinyin = match.group("pinyin")
                defs = [
                    definition.strip()
                    for definition in match.group("defs").strip("/").split("/")
                    if definition.strip()
                ]
                entries.setdefault(simplified, (pinyin, defs))
        return cls(entries)

    def lookup(self, hanzi: str) -> tuple[str, list[str]] | None:
        return self._entries.get(hanzi)

    def english_gloss(self, hanzi: str) -> str:
        entry = self.lookup(hanzi)
        if not entry:
            return ""
        return "; ".join(entry[1])

    def numbered_pinyin(self, hanzi: str) -> str:
        entry = self.lookup(hanzi)
        if not entry:
            return ""
        return entry[0].replace(" ", "")


def fetch_cedict(target_path: Path | None = None) -> Path:
    """Download and decompress CC-CEDICT to data/cedict_ts.u8."""
    import gzip
    import shutil
    import subprocess

    destination = target_path or CEDICT_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    gz_path = destination.with_suffix(".u8.gz")

    try:
        urllib.request.urlretrieve(CEDICT_URL, gz_path)
    except Exception:
        subprocess.run(
            ["curl", "-fsSL", CEDICT_URL, "-o", str(gz_path)],
            check=True,
        )

    with gzip.open(gz_path, "rb") as gz_handle, destination.open("wb") as out_handle:
        shutil.copyfileobj(gz_handle, out_handle)
    gz_path.unlink(missing_ok=True)
    return destination


def ensure_cedict(path: Path | None = None) -> CedictLookup:
    dictionary_path = path or CEDICT_PATH
    if not dictionary_path.exists():
        fetch_cedict(dictionary_path)
    return CedictLookup.load(dictionary_path)
