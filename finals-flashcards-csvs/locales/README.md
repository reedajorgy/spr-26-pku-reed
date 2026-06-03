# Locale overlays (mother languages)

Master decks live in the parent folder and are **never modified**:

- `kouyu-qimo-vocab.csv`, `jingdu-qimo-vocab.csv`
- `kouyu-qimo-grammar.csv`, `jingdu-qimo-grammar.csv`
- `jingdu-qimo-differences.csv`

Each supported language has its own subdirectory with **five mirrored overlay files**:

```text
locales/
  manifest.json
  ru/
  ko/
  ja/
  es/
  vi/
  hi/
  fr/
```

## Default language

**English** comes from the master CSVs. Overlays are used only when you select another locale (`ru`, `ko`, `ja`, `es`, `vi`, `hi`, `fr`). If an overlay cell is empty, the merge falls back to the master English text.

## Join keys

| Deck | Keys |
|------|------|
| `*-vocab` | `Chapter`, `hanzi` |
| `jingdu-qimo-grammar` | `Chapter`, `Grammar Point` |
| `kouyu-qimo-grammar` | `Chapter`, `Pattern Template` |
| `jingdu-qimo-differences` | `Chapter`, `Word Pair`, `Word` |

Chinese, pinyin, and Mandarin definition columns always come from the master.

## Regenerate overlays

```bash
# Skeleton (join keys only)
PYTHONPATH=. python apps/flashcards/scaffold_locales.py

# Fill overlays from hand-authored translation modules (see apps/flashcards/locale_data/)
PYTHONPATH=. python apps/flashcards/write_overlay_csv.py --deck kouyu-qimo-vocab --locale fr \\
  --translations apps/flashcards/locale_data/fr/kouyu_qimo_vocab.py

# Validate keys match masters
PYTHONPATH=. python apps/flashcards/validate_locales.py --require-filled
```

## Web study preview

```bash
./run_flashcards_web.sh
# Open http://127.0.0.1:8765
```

Filters and mother language persist in the browser (`spr26_study_settings`). Study mode uses the same reveal buttons as Anki (汉字 / 拼音 / Gloss / 例句). Re-import the `.apkg` after template changes (see below).

## Anki export

```bash
# Master deck (all courses, chapters, aspects, locales in one .apkg)
./run_build_master_finals_anki.sh
# -> outputs/finals-master.apkg
# Re-import in Anki after template/CSS changes. Mother language is under ⚙ Study settings
# (saved in localStorage). Example sentences stay hidden until 例句 or Show Answer.

# Kouyu vocab only (legacy, single locale)
./run_build_kouyu_anki.sh --locale fr --output outputs/kouyu-qimo-vocab-fr.apkg

# Any single deck, single locale
./run_build_finals_anki.sh --deck jingdu-qimo-vocab --locale ru
./run_build_finals_anki.sh --all --locale ko
```

Master deck hierarchy is defined in `manifest.json` under `courses` and `aspects`.

## Adding a new word

1. Add the row to the **master** CSV only.
2. Run `scaffold_locales.py` (or add one row manually to each locale file with the same join keys).
3. Fill translation columns for each language.
4. Run `validate_locales.py`.
