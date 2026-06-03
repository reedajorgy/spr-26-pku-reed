from __future__ import annotations

import unittest
from pathlib import Path

from apps.flashcards.locale_manifest import get_deck_specs, list_supported_locales
from apps.flashcards.merge import merge_deck_to_records
from apps.flashcards.paths import FINALS_DIR, LOCALES_DIR, MANIFEST_PATH
from apps.flashcards.web.app import STATIC_DIR, app


class VercelDeployReadyTests(unittest.TestCase):
    def test_manifest_and_master_csvs_exist(self) -> None:
        self.assertTrue(MANIFEST_PATH.is_file(), f"Missing {MANIFEST_PATH}")
        specs = get_deck_specs()
        self.assertGreater(len(specs), 0)
        for deck_name, spec in specs.items():
            master_path = FINALS_DIR / spec.master_file
            self.assertTrue(
                master_path.is_file(),
                f"Missing master CSV for {deck_name}: {master_path}",
            )

    def test_locale_overlay_csvs_exist(self) -> None:
        specs = get_deck_specs()
        overlay_locales = [
            code for code in list_supported_locales() if code != "en"
        ]
        missing: list[str] = []
        for locale_code in overlay_locales:
            locale_dir = LOCALES_DIR / locale_code
            if not locale_dir.is_dir():
                missing.append(f"{locale_code}/ (directory)")
                continue
            for deck_name in specs:
                overlay_path = locale_dir / f"{deck_name}.csv"
                if not overlay_path.is_file():
                    missing.append(str(overlay_path.relative_to(FINALS_DIR)))
        self.assertEqual(
            missing,
            [],
            "Missing locale overlay CSVs:\n" + "\n".join(missing),
        )

    def test_static_assets_exist(self) -> None:
        for name in ("index.html", "app.js", "styles.css"):
            path = STATIC_DIR / name
            self.assertTrue(path.is_file(), f"Missing static file: {path}")

    def test_sample_merge_per_locale(self) -> None:
        for locale_code in ("en", "fr", "ru", "ja"):
            records = merge_deck_to_records(
                "kouyu-qimo-vocab",
                locale_code,
                finals_dir=FINALS_DIR,
            )
            self.assertGreater(len(records), 0, locale_code)
            meaning = records[0]["translations"]["meaning"]
            self.assertTrue(meaning.strip(), locale_code)

    def test_fastapi_app_import(self) -> None:
        self.assertIsNotNone(app)
        self.assertEqual(app.title, "Reed's Finals Flashcards")

    def test_main_exports_fastapi_app(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        python_deps = repo_root / "python_deps"
        self.assertTrue(
            python_deps.is_dir(),
            "Run: python3 -m pip install -r requirements.txt -t python_deps",
        )
        from main import app as vercel_app

        self.assertEqual(getattr(vercel_app, "title", None), "Reed's Finals Flashcards")


if __name__ == "__main__":
    unittest.main()
