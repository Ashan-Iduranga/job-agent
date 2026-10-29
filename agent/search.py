"""Agent web search: headless Claude finds vacancies beyond the fixed sources."""
from __future__ import annotations

import json
import logging
from datetime import date
from urllib.parse import urlparse

from .claude_cli import ClaudeError, run_claude
from .config import DATA_DIR, PROMPTS_DIR, load_sources_config
from .deadlines import parse_date
from .models import Job

log = logging.getLogger(__name__)

RESULTS = DATA_DIR / "search_results.json"


def _domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def known_domains() -> tuple[set[str], set[str], list[str]]:
    """(domains already scraped, domains never to touch, companies to look up by search)."""
    cfg = load_sources_config()
    sources = cfg.get("sources", [])
    scraped = {_domain(u) for s in sources if s.get("enabled") for u in s.get("urls", [])}
    blocked = {d.lower() for d in cfg.get("blocked_domains", [])}
    watch = [s.get("company", s["name"]) for s in sources if not s.get("enabled")]
    return scraped, blocked, watch


def _is_under(domain: str, roots: set[str]) -> bool:
    return any(domain == r or domain.endswith("." + r) for r in roots)


def web_search(dry_run: bool = False) -> tuple[list[Job], list[tuple[str, str]]]:
    """Run the search prompt. Returns (jobs, [(new_domain, example_url)]) for suggested sources."""
    scraped, blocked, watch = known_domains()
    skip = sorted(blocked | scraped)
    prompt = ((PROMPTS_DIR / "search.md").read_text(encoding="utf-8")
              .replace("{today}", date.today().isoformat())
              .replace("{watch_companies}", ", ".join(watch) or "none")
              .replace("{skip_domains}", ", ".join(skip)))
    RESULTS.unlink(missing_ok=True)
    run_claude(prompt, "Read,Write,WebSearch,WebFetch")
    if not RESULTS.exists():
        raise ClaudeError("claude did not write data/search_results.json")
    items = json.loads(RESULTS.read_text(encoding="utf-8"))

    jobs: list[Job] = []
    suggestions: dict[str, str] = {}
    for it in items if isinstance(items, list) else []:
        url = str(it.get("url") or "").strip()
        title = str(it.get("title") or "").strip()
        if not url.startswith("http") or not title:
            continue
        dom = _domain(url)
        if _is_under(dom, blocked):
            continue  # never store links to sites that forbid scraping
        jobs.append(Job(
            title=title, company=str(it.get("company") or "Unknown").strip(), url=url, source="web_search",
            location=str(it.get("location") or ""), job_type=str(it.get("job_type") or ""),
            posted=parse_date(it.get("posted")), deadline=parse_date(it.get("deadline")),
            description=str(it.get("description") or "")[:1500],
        ))
        if not _is_under(dom, scraped):
            suggestions.setdefault(dom, url)
    log.info("web_search: %d job(s), %d new domain(s)%s", len(jobs), len(suggestions), " (dry run)" if dry_run else "")
    return jobs, list(suggestions.items())
