from __future__ import annotations

import csv
import unittest
from pathlib import Path

from apps.flashcards.export_sem1_csv import CSV_HEADER, MASTER_HEADER, build_sem1_csv_rows
from apps.flashcards.paths import FINALS_DIR
from apps.flashcards.pinyin_tone import numbered_pinyin_to_tone_marks
from apps.flashcards.sem1_enrich import enrich_source_row, enrich_source_rows
from apps.flashcards.sem1_merge import merge_enriched_rows, resolve_export_category
from apps.flashcards.sem1_source import parse_sem1_source

SOURCE_PATH = FINALS_DIR / "Pku Sem 1.txt"


class Sem1ImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_rows = parse_sem1_source(SOURCE_PATH)
        try:
            from apps.flashcards.cedict_lookup import CedictLookup

            cls.cedict = CedictLookup.load()
        except FileNotFoundError:
            cls.cedict = None
        cls.enriched_rows = enrich_source_rows(cls.source_rows, cedict=cls.cedict)
        cls.merged_rows, cls.grouped, cls.stats = build_sem1_csv_rows(
            SOURCE_PATH,
            cedict=cls.cedict,
        )

    def test_september_chengyu_section_parsed(self) -> None:
        september_idioms = [
            row for row in self.source_rows if row.chapter == "September 2025/成语"
        ]
        self.assertGreaterEqual(len(september_idioms), 30)
        self.assertEqual(september_idioms[0].hanzi, "怡情养性")

    def test_pinyin_tone_conversion(self) -> None:
        cases = {
            "yi2qing2yang3xing4": "yíqíngyǎngxìng",
            "wu2lun4ru2he2": "wúlùnrúhé",
            "da1cha2r5": "dāchár",
            "kai1li4 zhang4hu4": "kāilì zhànghù",
            "da3//xiang3zhi3": "dǎ xiǎngzhǐ",
        }
        for numbered, expected in cases.items():
            self.assertEqual(numbered_pinyin_to_tone_marks(numbered), expected)

    def test_merge_duplicate_headword(self) -> None:
        merged = merge_enriched_rows(self.enriched_rows)
        unbelievable = [row for row in merged if row.hanzi == "不可思议"]
        self.assertEqual(len(unbelievable), 1)
        self.assertIn("September 2025/成语", unbelievable[0].chapter)
        self.assertIn("；", unbelievable[0].chapter)

    def test_category_priority_for_cross_type_headword(self) -> None:
        category = resolve_export_category({"vocab", "chengyu"})
        self.assertEqual(category, "chengyu")
        literature_category = resolve_export_category({"literature-vocab", "literature-chengyu"})
        self.assertEqual(literature_category, "literature-chengyu")

    def test_export_schema_complete(self) -> None:
        for row in self.merged_rows:
            self.assertTrue(row.hanzi)
            self.assertTrue(row.pinyin, msg=f"missing pinyin: {row.hanzi}")
            self.assertTrue(row.english_meaning, msg=f"missing English: {row.hanzi}")
            self.assertTrue(row.mandarin_meaning, msg=f"missing Mandarin: {row.hanzi}")

    def test_gap_fill_for_empty_source_gloss(self) -> None:
        empty_source = [row for row in self.source_rows if row.hanzi == "搭碴儿"][0]
        self.assertEqual(empty_source.raw_gloss, "")
        enriched = enrich_source_row(empty_source, cedict=self.cedict)
        self.assertTrue(enriched.english_meaning)
        self.assertTrue(enriched.mandarin_meaning)
        self.assertEqual(enriched.pinyin, "dāchár")

    def test_written_csv_files_exist_with_headers(self) -> None:
        for filename in (
            "pku-sem1-chengyu.csv",
            "pku-sem1-proper-nouns.csv",
            "pku-sem1-vocab.csv",
            "pku-sem1-literature-chengyu.csv",
            "pku-sem1-literature-vocab.csv",
            "pku-sem1-literature-proper-nouns.csv",
            "pku-sem1-master.csv",
        ):
            path = FINALS_DIR / filename
            self.assertTrue(path.exists(), msg=f"missing {filename}")
            with path.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                expected_header = MASTER_HEADER if filename.endswith("master.csv") else CSV_HEADER
                self.assertEqual(reader.fieldnames, expected_header)
                first_row = next(reader, None)
                self.assertIsNotNone(first_row)

    def test_merge_counts(self) -> None:
        self.assertEqual(self.stats["source_rows"], 2768)
        self.assertEqual(self.stats["merged_rows"], 2457)
        self.assertEqual(self.stats["empty_english_after_enrich"], 0)
        self.assertEqual(self.stats["empty_mandarin_after_enrich"], 0)

    def test_sem1_anki_package_builds(self) -> None:
        from apps.flashcards.sem1_anki import build_sem1_package, summarize_sem1_package

        package = build_sem1_package(finals_dir=FINALS_DIR)
        self.assertGreater(len(package.decks), 0)
        note_count, card_count, subdeck_counts = summarize_sem1_package(finals_dir=FINALS_DIR)
        self.assertEqual(note_count, 2457)
        self.assertEqual(card_count, 4914)
        self.assertGreater(len(subdeck_counts), 0)


if __name__ == "__main__":
    unittest.main()
