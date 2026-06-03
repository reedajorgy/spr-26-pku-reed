from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from apps.flashcards.anki_master import aspect_subdeck_name, summarize_master_package
from apps.flashcards.merge import merge_deck_rows_multilocale, merge_vocab_for_anki_multilocale
from apps.flashcards.paths import FINALS_DIR


class FlashcardMultilocaleTests(unittest.TestCase):
    def test_multilocale_real_kouyu_chapter_7_vocab_count(self) -> None:
        rows = merge_deck_rows_multilocale("kouyu-qimo-vocab", finals_dir=FINALS_DIR)
        chapter_seven = [
            row for row in rows if row["master"].get("Chapter") == "Chapter 7"
        ]
        self.assertGreater(len(chapter_seven), 0)
        first = chapter_seven[0]
        self.assertEqual(
            first["translations"]["meaning"]["en"],
            first["master"]["英文意义"],
        )
        self.assertIn("meaning", first["translations"])
        self.assertIn("ru", first["translations"]["meaning"])

    def test_overlay_empty_falls_back_to_english(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            finals_dir = Path(temp_dir)
            locales_dir = finals_dir / "locales"
            (locales_dir / "fr").mkdir(parents=True)

            master_path = finals_dir / "kouyu-qimo-vocab.csv"
            with master_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        "Chapter",
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
                    ],
                )
                writer.writerow(
                    [
                        "Chapter 7",
                        "测试",
                        "cèshì",
                        "试验。",
                        "test",
                        "动",
                        "",
                        "中性",
                        "我们测试。",
                        "We test.",
                        "",
                        "",
                        "",
                    ],
                )

            overlay_path = locales_dir / "fr" / "kouyu-qimo-vocab.csv"
            with overlay_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Chapter", "hanzi", "meaning", "example_en", "usage_note"])
                writer.writerow(["Chapter 7", "测试", "", "", ""])

            merged = merge_deck_rows_multilocale(
                "kouyu-qimo-vocab",
                finals_dir=finals_dir,
                locales_dir=locales_dir,
            )
            self.assertEqual(merged[0]["translations"]["meaning"]["fr"], "test")

    def test_vocab_anki_fields_include_all_locales(self) -> None:
        rows = merge_vocab_for_anki_multilocale("kouyu-qimo-vocab", finals_dir=FINALS_DIR)
        self.assertIn("Meaning_en", rows[0])
        self.assertIn("Meaning_fr", rows[0])
        self.assertIn("ExampleEn_en", rows[0])

    def test_aspect_subdeck_path(self) -> None:
        path = aspect_subdeck_name(
            "PKU Spring 2026 Finals",
            "Kouyu",
            "Chapter 7",
            "Vocab",
        )
        self.assertEqual(path, "PKU Spring 2026 Finals::Kouyu::Chapter_7::Vocab")

    def test_master_summary_counts(self) -> None:
        note_count, card_count, subdeck_counts = summarize_master_package(finals_dir=FINALS_DIR)
        self.assertGreater(note_count, 600)
        self.assertGreater(card_count, note_count)
        self.assertIn("PKU Spring 2026 Finals::Kouyu::Chapter_7::Vocab", subdeck_counts)


if __name__ == "__main__":
    unittest.main()
