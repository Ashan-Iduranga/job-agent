"""Generic company careers page: collect links matching a per-company URL pattern.

sources.yaml options:
  link_pattern:   regex a job link's href must match (required)
  title_selector: CSS selector for the title inside the link (optional; default = link text)
  company:        company name to store (default = source name)
  location:       default location (optional)
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Job
from .base import Source

log = logging.getLogger(__name__)


class CareersPage(Source):
    def fetch(self) -> list[Job]:
        pattern = re.compile(self.config["link_pattern"])
        sel = self.config.get("title_selector")
        company = self.config.get("company", self.name)
        jobs: dict[str, Job] = {}
        for url in self.urls:
            resp = self.client.get(url)
            soup = BeautifulSoup(resp.content.decode("utf-8", "replace"), "html.parser")
            for a in soup.find_all("a", href=True):
                href = urljoin(resp.url, a["href"])
                if not pattern.search(href) or href in jobs:
                    continue
                t = a.select_one(sel) if sel else None
                title = (t or a).get_text(" ", strip=True)
                if not title or title.lower() in {"apply now", "apply", "read more", "view"}:
                    continue
                full = a.get_text(" | ", strip=True)  # tags such as country / type help ranking
                jobs[href] = Job(title=title, company=company, url=href, source=self.name,
                                 location=self.config.get("location", ""),
                                 description=full if full != title else "",
                                 extra={"it_category": bool(self.config.get("it_company", True))})
        log.info("%s: found %d job links", self.name, len(jobs))
        return list(jobs.values())


SOURCE_CLASS = CareersPage
