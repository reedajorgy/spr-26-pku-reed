"""
Lecture-to-bilingual-review pipeline package.

This package exposes a CLI entrypoint in build_review.py that:
- Takes a transcript filepath as input.
- Calls an LLM (e.g. DeepSeek) with carefully designed prompts.
- Produces structured JSON review data for downstream use.
"""

