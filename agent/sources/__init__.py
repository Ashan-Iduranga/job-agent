"""Source registry: maps sources.yaml entries to Source classes."""
from __future__ import annotations

import importlib
from typing import Any

from ..http import PoliteClient
from .base import Source


def load_source(entry: dict[str, Any], client: PoliteClient) -> Source:
    """Instantiate the Source subclass from agent/sources/<module>.py."""
    module = importlib.import_module(f"{__name__}.{entry['module']}")
    cls = getattr(module, "SOURCE_CLASS")
    return cls(entry["name"], entry, client)


def enabled_entries(config: dict[str, Any], only: str | None = None) -> list[dict[str, Any]]:
    """Source entries to run. --source forces a source on even if disabled."""
    entries = config.get("sources", [])
    if only:
        return [e for e in entries if e["name"] == only]
    return [e for e in entries if e.get("enabled", True)]
