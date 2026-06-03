English | [中文](README_zh.md)

## Project overview

This repository contains small tools to support **Chinese language study from real course materials**:

- **Audio transcription pipeline**: turns recorded lectures into cleaned, timestamped transcripts.
- **口语 / 精读 vocabulary tools**: read transcripts or textbook-like content and build structured vocabulary lists.
- **Class summarizer** (planned): turn final transcripts into structured summaries and homework notes.

The code is opinionated around one concrete course, but is intended to be reusable for other learners who have their own raw materials.

## Directory layout
^
- `raw_materials/` (ignored by git)
  - `audio_lectures/`: raw audio files (e.g. `.m4a`, `.wav`) from classes.
  - `textbooks/`: textbook PDFs and other reference documents.
  - `first_pass_transcripts/`: rough or intermediate transcripts that should remain private.
- `apps/`
  - `transcriber/`: code for offline transcription (e.g. using faster-whisper or other backends).
  - `textbook_vocab/`: tooling for building vocabulary lists from textbook or transcript content.
  - `flashcards/`: merge master finals CSVs with locale overlays; web settings UI; Anki export helpers.
  - `class_summarizer/`: LLM-powered summarization of final class transcripts (not yet implemented).
- `finals-flashcards-csvs/`: master vocab/grammar/difference CSVs plus `locales/{ru,ko,ja,es,vi,hi,fr}/` translation overlays (masters are never edited by locale tools).
- `outputs/`: generated artifacts such as cleaned transcripts, vocabulary CSVs, and summary drafts.
- `old_materials/`: legacy scripts and notes kept around for reference.
- `scripts/`: small shell helpers for running common workflows (e.g. transcription, vocab extraction).

## Privacy and raw materials

Raw media and private study materials **must remain local** and are never pushed to GitHub:

- All lecture recordings, textbook PDFs, and personal notes live under `raw_materials/`.
- The root `.gitignore` is configured to ignore the entire `raw_materials/` tree.
- When sharing or forking this project, other users bring their own media by creating the same folder structure locally.

## Getting started (local)

1. Create and activate a Python virtual environment, for example:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
2. Install Python dependencies:
   - Web app only: `pip install -r requirements.txt`
   - Full repo (transcription, Anki, etc.): `pip install -r requirements-dev.txt`
3. Create the `raw_materials/` directory structure if it does not exist:
   - `raw_materials/audio_lectures/`
   - `raw_materials/textbooks/`
   - `raw_materials/first_pass_transcripts/`
4. Place your own lecture recordings, textbooks, and rough transcripts into the appropriate subfolders.
5. Run the convenience shell scripts in `scripts/` (for example `run_transcription.sh`) or call the individual apps under `apps/` directly, following any per-app README or inline help.

## Finals flashcards (multi-language)

Master decks are in `finals-flashcards-csvs/*.csv`. Mother-tongue glosses live in `finals-flashcards-csvs/locales/<code>/` (Russian, Korean, Japanese, Spanish, Vietnamese, Hindi, French). **English is the default** and is read from the masters; overlays replace only English-facing fields at preview/export time.

### Master Anki deck (recommended)

One import covers **口语 Kouyu** and **精读 Jingdu**, every chapter, vocab / grammar / word-differences, and **all mother languages** with an in-card dropdown (preference saved via `localStorage` on desktop Anki).

```bash
./run_build_master_finals_anki.sh
# or: PYTHONPATH=. python apps/flashcards/export_master_anki.py
# -> outputs/finals-master.apkg (Vocab + Grammar + Word_Differences for Kouyu & Jingdu)
```

**Subdeck layout:**

`PKU Spring 2026 Finals::Kouyu::Chapter_7::Vocab` (and parallel paths for Grammar, Word_Differences, etc.)

**Study tips:**

- Cram one chapter: enable only e.g. `Jingdu::Chapter_5` and its Vocab / Grammar subdecks.
- One class only: suspend everything outside `::Kouyu::` or `::Jingdu::`.
- Mother language: use the card’s **Mother language** menu once; desktop Anki remembers it. On some mobile clients the choice may not persist between sessions.

### Web study app (Reed's Finals Flashcards)

```bash
./run_flashcards_web.sh
# http://127.0.0.1:8765 — course, card type, chapter filters + local study progress
```

#### Deploy on Vercel

The web UI is a FastAPI app served from `api/index.py`. Vercel installs dependencies from root `requirements.txt` and `pyproject.toml` (FastAPI + Mangum + uvicorn).

**Tracked for Git / Vercel (the app):**

| Path | Role |
|------|------|
| `api/` | Serverless entry |
| `apps/flashcards/web/`, `merge.py`, `hierarchy.py`, `locale_manifest.py`, `paths.py`, `study_prefs.py` | Runtime code |
| `finals-flashcards-csvs/` | Master decks + `locales/{en,ru,ko,ja,es,vi,hi,fr}/` overlays |
| `vercel.json`, `.vercelignore`, `run_flashcards_web.sh` | Deploy + local dev |

**Ignored via `.gitignore`** (stay local only): `apps/transcriber/`, `apps/textbook_vocab/`, `scripts/`, `outputs/`, Anki builders, `locale_data/` authoring, other `run_*.sh`, etc.

1. Commit and push to GitHub.
2. [Vercel](https://vercel.com/new) → import repo. **Critical dashboard settings:** Root Directory = repo root; **Build Command** and **Output Directory** overrides must be **OFF** (empty). If Output Directory is `public` or `dist`, you will get **404 on every URL**. See [docs/VERCEL_SETUP.md](docs/VERCEL_SETUP.md).
3. `vercel.json` uses `builds` + `@vercel/python` on `api/index.py` so Vercel actually creates a Python function (rewrites alone are not enough on Framework Preset “Other”).
4. Deploy with **Clear build cache**. Build log should mention Python/`api/index.py`, not finish in ~14ms with no function.

**Pre-deploy check:**

```bash
pip install -r requirements.txt
export PYTHONPATH=.
python -m unittest tests.test_vercel_deploy_ready -v
python -m uvicorn apps.flashcards.web.app:app --reload --port 8765
```

If you previously committed ignored paths, stop tracking them once:  
`git rm -r --cached scripts outputs apps/transcriber apps/textbook_vocab 2>/dev/null; true`

### Single-deck Anki exports (legacy / overlay editing)

- **Kouyu vocab**: `./run_build_kouyu_anki.sh --locale fr`
- **Any deck, one locale**: `./run_build_finals_anki.sh --deck jingdu-qimo-vocab --locale ru`

See [finals-flashcards-csvs/locales/README.md](finals-flashcards-csvs/locales/README.md) for overlay layout, validation, and regeneration commands.

## Transcription (recommended workflow)

### Interactive (pick multiple files, sequential)
Run:
- `./run_transcription.sh`

You can select multiple indices like `0,2,5-7`. The runner processes them **in series** and prompts you for number of passes and CPU thread usage.

Outputs:
- If you choose **1 pass** (default): `raw_materials/first_pass_transcripts/<relpath>.txt` and `raw_materials/final_transcripts/<relpath>.txt`\n+- If you choose **2 passes**: `raw_materials/first_pass_transcripts/<relpath>.run1.txt` and `.run2.txt`, plus `raw_materials/final_transcripts/<relpath>.txt` (and optional `.diff.txt` when disagreement is high)

### Batch / long unattended runs (queue + CPU “power” knob)
Run:
- `./run_transcription.sh --batch --runs 2 --power medium --resume`

Useful options:
- `--queue-file queue.txt`: one audio path per line (absolute or relative to `--input-dir`)
- `--limit N`: only do N items (good for incremental runs)
- `--shuffle`: randomize order
- `--cpu-threads K`: explicit cap
- `--max-workers 1`: force strict serial processing


