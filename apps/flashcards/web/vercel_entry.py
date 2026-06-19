"""
Shared Vercel/local bootstrap: sys.path, vendored deps, FastAPI app export.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DEPS = REPO_ROOT / "python_deps"
if PYTHON_DEPS.is_dir():
    sys.path.insert(0, str(PYTHON_DEPS))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_import_error: str | None = None
fastapi_app: Any = None

try:
    from apps.flashcards.web.app import app as fastapi_app  # noqa: E402

    app = fastapi_app
except Exception as import_error:
    _import_error = repr(import_error)

    async def app(scope, receive, send):  # type: ignore[no-redef]
        if scope.get("type") != "http":
            return
        body = (
            f"Reed's Finals Flashcards failed to start: {_import_error}".encode("utf-8")
        )
        await send(
            {
                "type": "http.response.start",
                "status": 500,
                "headers": [[b"content-type", b"text/plain; charset=utf-8"]],
            },
        )
        await send({"type": "http.response.body", "body": body})
