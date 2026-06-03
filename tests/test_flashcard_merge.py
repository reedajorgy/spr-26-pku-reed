from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from apps.flashcards.merge import merge_deck_rows, merge_vocab_for_anki
from apps.flashcards.paths import FINALS_DIR


class FlashcardMergeTests(unittest.TestCase):
    def test_english_passthrough_kouyu_vocab(self) -> None:
        rows = merge_vocab_for_anki("kouyu-qimo-vocab", "en", finals_dir=FINALS_DIR)
        self.assertGreater(len(rows), 0)
        first = rows[0]
        self.assertIn("Hanzi", first)
        self.assertIn("English", first)
        self.assertTrue(first["Hanzi"])

    def test_overlay_override_and_fallback(self) -> None:
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
                        "Chapter 5",
                        "测试",
                        "cèshì",
                        "试验。",
                        "test",
                        "动",
                        "～一下",
                        "中性",
                        "我们测试一下。",
                        "We run a test.",
                        "Short note.",
                        "",
                        "考试",
                    ],
                )
                writer.writerow(
                    [
                        "Chapter 5",
                        "空白",
                        "kòngbái",
                        "空。",
                        "blank",
                        "形",
                        "",
                        "中性",
                        "页是空白的。",
                        "The page is blank.",
                        "",
                        "",
                        "",
                    ],
                )

            overlay_path = locales_dir / "fr" / "kouyu-qimo-vocab.csv"
            with overlay_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Chapter", "hanzi", "meaning", "example_en", "usage_note"])
                writer.writerow(["Chapter 5", "测试", "essai", "Nous faisons un essai.", "Note courte."])

            merged = merge_deck_rows(
                "kouyu-qimo-vocab",
                "fr",
                finals_dir=finals_dir,
                locales_dir=locales_dir,
            )
            self.assertEqual(merged[0]["英文意义"], "essai")
            self.assertEqual(merged[0]["example_sentence_en"], "Nous faisons un essai.")
            self.assertEqual(merged[1]["英文意义"], "blank")


if __name__ == "__main__":
    unittest.main()
