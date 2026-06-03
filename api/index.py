"""
Vercel serverless entrypoint for the flashcards web app.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_DEPS = REPO_ROOT / "python_deps"
if PYTHON_DEPS.is_dir():
    sys.path.insert(0, str(PYTHON_DEPS))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# region agent log
from apps.flashcards.web.deploy_debug import DEPLOY_DIAGNOSTICS, agent_log

agent_log(
    "H1",
    "api/index.py:startup",
    "entrypoint module loading",
    {
        "repo_root": str(REPO_ROOT),
        "python_deps_dir": str(PYTHON_DEPS),
        "python_deps_exists": PYTHON_DEPS.is_dir(),
        "sys_path_head": sys.path[:8],
        "python_version": sys.version,
    },
)
# endregion

_import_error: str | None = None
fastapi_app: Any = None

try:
    # region agent log
    import fastapi as fastapi_module

    agent_log(
        "H2",
        "api/index.py:fastapi",
        "fastapi import ok",
        {"version": getattr(fastapi_module, "__version__", "unknown")},
    )
    # endregion

    from apps.flashcards.web.app import app as fastapi_app  # noqa: E402

    # region agent log
    agent_log(
        "H3",
        "api/index.py:fastapi_app",
        "fastapi application import ok",
        {"app_title": getattr(fastapi_app, "title", "")},
    )
    # endregion

    # Native ASGI app for Vercel Python 3.12+ (Mangum not required).
    app = fastapi_app

    # region agent log
    agent_log(
        "H4",
        "api/index.py:app_export",
        "exported ASGI app",
        {"app_type": type(app).__name__},
    )
    # endregion
except Exception as import_error:
    _import_error = repr(import_error)
    DEPLOY_DIAGNOSTICS["import_error"] = _import_error
    # region agent log
    agent_log(
        "H2",
        "api/index.py:import_failed",
        "entrypoint import failed",
        {"error": _import_error},
    )
    # endregion

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
