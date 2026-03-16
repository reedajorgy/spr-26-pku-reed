English | [中文](README_zh.md)

## Project overview

This repository contains small tools to support **Chinese language study from real course materials**:

- **Audio transcription pipeline**: turns recorded lectures into cleaned, timestamped transcripts.
- **口语 / 精读 vocabulary tools**: read transcripts or textbook-like content and build structured vocabulary lists.
- **Class summarizer** (planned): turn final transcripts into structured summaries and homework notes.

The code is opinionated around one concrete course, but is intended to be reusable for other learners who have their own raw materials.

## Directory layout

- `raw_materials/` (ignored by git)
  - `audio_lectures/`: raw audio files (e.g. `.m4a`, `.wav`) from classes.
  - `textbooks/`: textbook PDFs and other reference documents.
  - `first_pass_transcripts/`: rough or intermediate transcripts that should remain private.
- `apps/`
  - `transcriber/`: code for offline transcription (e.g. using faster-whisper or other backends).
  - `textbook_vocab/`: tooling for building vocabulary lists from textbook or transcript content.
  - `class_summarizer/`: LLM-powered summarization of final class transcripts (not yet implemented).
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
   - `pip install -r requirements.txt`
3. Create the `raw_materials/` directory structure if it does not exist:
   - `raw_materials/audio_lectures/`
   - `raw_materials/textbooks/`
   - `raw_materials/first_pass_transcripts/`
4. Place your own lecture recordings, textbooks, and rough transcripts into the appropriate subfolders.
5. Run the convenience shell scripts in `scripts/` (for example `run_transcription.sh`) or call the individual apps under `apps/` directly, following any per-app README or inline help.

