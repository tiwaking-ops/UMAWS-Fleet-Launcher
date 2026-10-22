"""Adapter registry (fleet amendment section 12.B).

One place that knows which adapter handles which CLI.
"""

from __future__ import annotations

from pathlib import Path

from .base import BaseAdapter, Caps, ResumeUnsupported
from .fake import FakeAdapter
from .generic import TemplateAdapter, make_real_adapter

__all__ = [
    "BaseAdapter", "Caps", "ResumeUnsupported", "FakeAdapter",
    "TemplateAdapter", "get_adapter", "known_adapters",
]

#: Adapters the Fleet ships.
KNOWN = ("hermes", "kilo", "cline", "pi", "opencode", "fake")


def known_adapters() -> tuple[str, ...]:
    return KNOWN


def get_adapter(name: str, fixture_root: str | Path | None = None) -> BaseAdapter:
    """Return the adapter for *name*.

    An unknown name falls back to the template adapter, which is the right
    behaviour for a profile that points at some other CLI: the argv template
    still works, only the capabilities are unknown.
    """
    if name == "fake":
        adapter = FakeAdapter(fixture_root)
    else:
        adapter = make_real_adapter(name, fixture_root)
    adapter.load_patterns(fixture_root)
    return adapter
