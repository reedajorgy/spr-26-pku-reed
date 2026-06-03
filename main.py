"""
Root FastAPI entrypoint for Vercel (serves /, /api/*, /static/* on one function).
"""
from __future__ import annotations

from apps.flashcards.web.vercel_entry import app

__all__ = ["app"]
