#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -d "$PROJECT_ROOT/.venv" ]]; then
  python3 -m venv "$PROJECT_ROOT/.venv"
fi

source "$PROJECT_ROOT/.venv/bin/activate"

cd "$PROJECT_ROOT"

export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"

python -m apps.transcriber.run_transcription

