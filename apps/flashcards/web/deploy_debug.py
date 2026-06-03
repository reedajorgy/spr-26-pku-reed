"""Debug logging for Vercel/local deploy diagnostics (session bf46e6)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

DEBUG_LOG_PATH = Path(__file__).resolve().parents[3] / ".cursor/debug-bf46e6.log"
DEPLOY_DIAGNOSTICS: dict[str, Any] = {}


def agent_log(
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict[str, Any] | None = None,
    run_id: str = "pre-fix",
) -> None:
    payload = {
        "sessionId": "bf46e6",
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    try:
        with DEBUG_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
    except OSError:
        pass
