"""xpress.jobs: the site's own JSON search API (the web page itself is a JavaScript app).

robots.txt allows everything. We query the IT sectors at entry level, plus intern/trainee
keyword searches within those sectors.
"""
from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlencode

from ..deadlines import parse_date
from ..models import Job
from .base import Source

log = logging.getLogger(__name__)

API = "https://xpress.jobs/api/jobs/searchJobs?"
JOB_URL = "https://xpress.jobs/jobs/view/{id}/{slug}"
IT_SECTORS = "30,139"  # IT-SWare / Internet, IT-HWare / Networks / Systems
ENTRY_LEVEL = "1"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


class Xpress(Source):
    def _search(self, page: int = 1, keyword: str = "", levels: str = "") -> list[dict[str, Any]]:
        params = {
            "page": page, "pageSize": 20, "keyword": keyword, "locations": "",
            "sectors": self.config.get("sectors", IT_SECTORS), "jobTypes": "", "careerLevels": levels,
            "sortBy": "SortedCreateDate DESC", "byCVLess": "false", "byWalkIn": "false",
        }
        data = self.client.get(API + urlencode(params), headers={"Accept": "application/json"}).json()
        if not isinstance(data, list):
            raise ValueError("xpress API response changed (expected a list)")
        return data

    def fetch(self) -> list[Job]:
        raw: dict[int, dict[str, Any]] = {}
        for page in range(1, int(self.config.get("pages", 3)) + 1):
            items = self._search(page=page, levels=ENTRY_LEVEL)
            raw.update({i["jobId"]: i for i in items})
            if len(items) < 20:
                break
        for kw in self.config.get("keywords", ["intern", "trainee"]):
            raw.update({i["jobId"]: i for i in self._search(keyword=kw)})
        jobs = [self._to_job(i) for i in raw.values() if i.get("jobId") and i.get("jobTitle")]
        log.info("xpress: %d jobs from API", len(jobs))
        return jobs

    def _to_job(self, i: dict[str, Any]) -> Job:
        title, org = i["jobTitle"].strip(), (i.get("organizationName") or "Unknown").strip()
        return Job(
            title=title, company=org,
            url=JOB_URL.format(id=i["jobId"], slug=_slug(f"{title} {org}")),
            source=self.name,
            location=(i.get("locations") or "").strip(" ,") + (" (remote)" if i.get("remote") else ""),
            job_type=i.get("jobType") or "",
            posted=parse_date(i.get("createdDate")),
            deadline=parse_date(i.get("expiryDateOnWebsite")),
            description=(i.get("overview") or "").strip(),
            extra={"it_category": True},
        )


SOURCE_CLASS = Xpress
