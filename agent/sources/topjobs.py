"""topjobs.lk: functional-area listing pages (IT categories)."""
from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from ..deadlines import parse_date
from ..models import Job
from .base import Source

log = logging.getLogger(__name__)

AD_URL = "https://www.topjobs.lk/employer/JobAdvertismentServlet?ac={ac}&jc={jc}&ec={ec}"
_ONCLICK = re.compile(r"createAlert\('(\d+)','([^']*)','([^']*)','([^']*)'")
_COUNT = re.compile(r"\s*\(\d+\)\s*$")  # "Intern - IT (3)" -> vacancies count suffix


def _clean(text: str) -> str:
    """topjobs serves some dashes/quotes as literal '?'; tidy them."""
    text = re.sub(r"\s\?\s", " - ", text).lstrip("?")
    return re.sub(r"\s+", " ", text).strip()


class TopJobs(Source):
    """Parses the vacancy table rows on topjobs.lk category pages."""

    def fetch(self) -> list[Job]:
        jobs: dict[str, Job] = {}
        for url in self.urls:
            resp = self.client.get(url)
            for job in self.parse(resp.content.decode(resp.encoding or "iso-8859-1", "replace")):
                jobs.setdefault(job.url, job)
        return list(jobs.values())

    def parse(self, html: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        out: list[Job] = []
        for tr in soup.select("tr[onclick*=createAlert]"):
            m = _ONCLICK.search(tr.get("onclick", ""))
            h2, h1 = tr.find("h2"), tr.find("h1")
            if not (m and h2 and h1):
                continue
            _, ac, jc, ec = m.groups()
            tds = tr.find_all("td", recursive=False)
            cell = lambda i: tds[i].get_text(" ", strip=True) if len(tds) > i else ""  # noqa: E731
            title_raw = h2.get_text(" ", strip=True)
            desc = cell(3)
            out.append(
                Job(
                    title=_clean(_COUNT.sub("", title_raw)),
                    company=_clean(h1.get_text(" ", strip=True)),
                    url=AD_URL.format(ac=ac, jc=jc, ec=ec),
                    source=self.name,
                    location=cell(6),
                    description="" if desc.lower().startswith("please refer") else desc,
                    posted=parse_date(cell(4)),
                    deadline=parse_date(cell(5)),
                    extra={"job_code": jc, "it_category": True},
                )
            )
        log.info("topjobs: parsed %d rows", len(out))
        return out


SOURCE_CLASS = TopJobs
