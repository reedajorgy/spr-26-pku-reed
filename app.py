"""
Root Vercel FastAPI entrypoint (zero-config routing for GET /).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent
PYTHON_DEPS = REPO_ROOT / "python_deps"
if PYTHON_DEPS.is_dir():
    sys.path.insert(0, str(PYTHON_DEPS))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# region agent log
from apps.flashcards.web.deploy_debug import DEPLOY_DIAGNOSTICS, agent_log

agent_log(
    "H1",
    "app.py:startup",
    "root entrypoint module loading",
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
        "app.py:fastapi",
        "fastapi import ok",
        {"version": getattr(fastapi_module, "__version__", "unknown")},
    )
    # endregion

    from apps.flashcards.web.app import app as fastapi_app  # noqa: E402

    # region agent log
    agent_log(
        "H3",
        "app.py:fastapi_app",
        "fastapi application import ok",
        {"app_title": getattr(fastapi_app, "title", "")},
    )
    # endregion

    app = fastapi_app

    # region agent log
    agent_log(
        "H4",
        "app.py:app_export",
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
        "app.py:import_failed",
        "root entrypoint import failed",
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
