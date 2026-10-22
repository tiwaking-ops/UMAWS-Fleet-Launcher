"""The UMAWS Fleet Console (FastAPI app and its static page)."""

from __future__ import annotations

__all__ = ["app", "Console", "main"]


def __getattr__(name: str):
    # Import lazily so that ``import console`` does not start the app.
    if name in ("app", "Console", "main"):
        from . import app as _app
        return getattr(_app, name)
    raise AttributeError(name)
