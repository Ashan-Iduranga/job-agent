"""itpro.lk: IT-only job board. Page 1 of the internship listing (robots.txt disallows ?p= paging)."""
from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from ..models import Job
from .base import Source

log = logging.getLogger(__name__)


class ItPro(Source):
    """Parses article.job-card elements."""

    def fetch(self) -> list[Job]:
        jobs: dict[str, Job] = {}
        for url in self.urls:
            resp = self.client.get(url)
            for job in self.parse(resp.content.decode("utf-8", "replace")):
                jobs.setdefault(job.url, job)
        return list(jobs.values())

    def parse(self, html: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        out: list[Job] = []
        for card in soup.select("article.job-card"):
            link, title = card.select_one("a.jcl[href]"), card.select_one(".jc-title")
            if not (link and title):
                continue
            company = card.select_one(".jc-company")
            meta = card.select_one(".jc-company-info span.la")
            loc, _, jtype = (meta.get_text(" ", strip=True) if meta else "").partition("•")
            posted = card.select_one("time[datetime]")
            out.append(Job(
                title=title.get_text(" ", strip=True),
                company=company.get_text(" ", strip=True) if company else "Unknown",
                url=link["href"], source=self.name, location=loc.strip(), job_type=jtype.strip(),
                posted=posted["datetime"][:10] if posted else None,
                extra={"it_category": True},  # IT-only board
            ))
        log.info("itpro: parsed %d cards", len(out))
        return out


SOURCE_CLASS = ItPro
