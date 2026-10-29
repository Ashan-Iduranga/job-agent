"""Core data model."""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text.lower())).strip()


@dataclass
class Job:
    """One vacancy as scraped from a source."""

    title: str
    company: str
    url: str
    source: str
    location: str = ""
    job_type: str = ""
    posted: str | None = None      # ISO date
    deadline: str | None = None    # ISO date
    description: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def key_hash(self) -> str:
        """Stable hash of title+company, catches the same job posted under different URLs."""
        return hashlib.sha1(f"{_norm(self.title)}|{_norm(self.company)}".encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["key_hash"] = self.key_hash
        return d
