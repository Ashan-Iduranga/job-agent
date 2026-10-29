"""Common interface every source implements."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..http import PoliteClient
from ..models import Job


class Source(ABC):
    """A job source. Subclasses implement fetch()."""

    def __init__(self, name: str, config: dict[str, Any], client: PoliteClient) -> None:
        self.name = name
        self.config = config
        self.client = client
        self.urls: list[str] = list(config.get("urls", []))

    @abstractmethod
    def fetch(self) -> list[Job]:
        """Return all vacancies currently listed (unfiltered)."""
