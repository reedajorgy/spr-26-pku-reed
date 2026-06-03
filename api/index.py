"""
Legacy /api/index path — re-exports the root Vercel entrypoint.
"""
from __future__ import annotations

from app import app

__all__ = ["app"]
