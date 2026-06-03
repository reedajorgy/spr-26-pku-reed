"""
Vercel serverless entrypoint for the flashcards web app.

Ensures the repository root is on PYTHONPATH so apps.flashcards.* and
finals-flashcards-csvs/ resolve the same way as local development.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.flashcards.web.app import app as fastapi_app  # noqa: E402
from mangum import Mangum  # noqa: E402

app = Mangum(fastapi_app, lifespan="off")
