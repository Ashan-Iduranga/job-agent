"""Polite HTTP client: clear User-Agent, robots.txt, per-host delay, retries."""
from __future__ import annotations

import logging
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import SETTINGS, USER_AGENT

log = logging.getLogger(__name__)


class RobotsDisallowed(Exception):
    """robots.txt forbids fetching this URL."""


class PoliteClient:
    """requests.Session wrapper that respects robots.txt and spaces out requests per host."""

    def __init__(self, delay: float | None = None) -> None:
        self.delay = SETTINGS.request_delay if delay is None else delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en"})
        retry = Retry(total=2, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504))
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.mount("http://", HTTPAdapter(max_retries=retry))
        self._robots: dict[str, RobotFileParser | None] = {}
        self._last_hit: dict[str, float] = {}

    def _robots_for(self, url: str) -> RobotFileParser | None:
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        if base not in self._robots:
            rp: RobotFileParser | None = None
            try:
                r = self.session.get(f"{base}/robots.txt", timeout=20, allow_redirects=False)
                # Only trust a real text robots file; redirects/HTML pages mean "no robots.txt".
                if r.status_code == 200 and "text/plain" in r.headers.get("content-type", ""):
                    rp = RobotFileParser()
                    rp.parse(r.text.splitlines())
            except requests.RequestException as exc:
                log.warning("robots.txt fetch failed for %s: %s", base, exc)
            self._robots[base] = rp
        return self._robots[base]

    def allowed(self, url: str) -> bool:
        rp = self._robots_for(url)
        return True if rp is None else rp.can_fetch(USER_AGENT, url)

    def get(self, url: str, **kwargs) -> requests.Response:
        """GET with robots check and per-host delay. Raises on HTTP errors."""
        if not self.allowed(url):
            raise RobotsDisallowed(url)
        host = urlparse(url).netloc
        rp = self._robots_for(url)
        crawl_delay = (rp.crawl_delay(USER_AGENT) if rp else None) or 0
        wait = max(self.delay, float(crawl_delay)) - (time.monotonic() - self._last_hit.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        kwargs.setdefault("timeout", 30)
        resp = self.session.get(url, **kwargs)
        self._last_hit[host] = time.monotonic()
        resp.raise_for_status()
        return resp
