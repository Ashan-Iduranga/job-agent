"""ikman.lk jobs: keyword searches, parsed from the page's embedded window.initialData JSON.

ikman has no IT job category, so we run a few searches (config `queries`) and let the
keyword filter drop the many non-IT results.
"""
from __future__ import annotations

import json
import logging
import re
from urllib.parse import quote

from ..deadlines import parse_date
from ..models import Job
from .base import Source

log = logging.getLogger(__name__)

SEARCH_URL = "https://ikman.lk/en/ads/sri-lanka/jobs?query={q}"
AD_URL = "https://ikman.lk/en/ad/{slug}"
_DATA = re.compile(r"window\.initialData\s*=\s*(\{.*?\})\s*</script>", re.S)


class Ikman(Source):
    def fetch(self) -> list[Job]:
        jobs: dict[str, Job] = {}
        for q in self.config.get("queries", ["intern", "trainee"]):
            resp = self.client.get(SEARCH_URL.format(q=quote(q)))
            for job in self.parse(resp.content.decode("utf-8", "replace")):
                jobs.setdefault(job.url, job)
        return list(jobs.values())

    def parse(self, html: str) -> list[Job]:
        m = _DATA.search(html)
        if not m:
            raise ValueError("ikman page layout changed: window.initialData not found")
        ads = json.loads(m.group(1)).get("serp", {}).get("ads", {}).get("data", {}).get("ads", [])
        out = []
        for ad in ads:
            if not ad.get("slug") or not ad.get("isJobAd"):
                continue
            out.append(Job(
                title=ad.get("title", "").strip(),
                company=(ad.get("shopName") or ad.get("details") or "Unknown").strip(),
                url=AD_URL.format(slug=ad["slug"]), source=self.name,
                location=ad.get("location", ""), job_type=(ad.get("category") or {}).get("name", ""),
                posted=parse_date(f"{ad['timeStamp']} ago") if re.match(r"\d+ \w+$", ad.get("timeStamp", "")) else None,
                description=ad.get("description", ""),
            ))
        log.info("ikman: parsed %d ads", len(out))
        return out


SOURCE_CLASS = Ikman
