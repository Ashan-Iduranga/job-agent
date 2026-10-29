"""Pipeline CLI: scrape -> filter -> dedupe -> (web search) -> rank.

Usage:
    python -m agent.main                 # full run
    python -m agent.main --dry-run       # scrape + filter + print, nothing saved
    python -m agent.main --source topjobs
    python -m agent.main --no-search     # skip the Claude web-search step
    python -m agent.main --rerank        # only rank jobs that have no score yet
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

from . import db
from .config import SETTINGS, ensure_dirs, load_sources_config
from .filter import filter_jobs
from .http import PoliteClient, RobotsDisallowed
from .models import Job
from .sources import enabled_entries, load_source

log = logging.getLogger("agent")


def scrape(only: str | None) -> tuple[list[Job], dict[str, dict[str, Any]]]:
    """Run every enabled source; one failure never stops the others."""
    config = load_sources_config()
    client = PoliteClient()
    all_jobs: list[Job] = []
    report: dict[str, dict[str, Any]] = {}
    entries = enabled_entries(config, only)
    if only and not entries:
        raise SystemExit(f"Unknown source '{only}'. Check sources.yaml.")
    for entry in entries:
        name = entry["name"]
        try:
            jobs = load_source(entry, client).fetch()
            kept = filter_jobs(jobs)
            report[name] = {"found": len(jobs), "kept": len(kept), "error": None}
            all_jobs.extend(kept)
            log.info("%-18s found %3d  kept %3d", name, len(jobs), len(kept))
        except RobotsDisallowed as exc:
            report[name] = {"found": 0, "kept": 0, "error": f"blocked by robots.txt: {exc}"}
            log.warning("%s blocked by robots.txt", name)
        except Exception as exc:  # noqa: BLE001 - isolate each source
            report[name] = {"found": 0, "kept": 0, "error": f"{type(exc).__name__}: {exc}"}
            log.exception("%s failed", name)
    return all_jobs, report


def print_jobs(jobs: list[Job]) -> None:
    for j in jobs:
        print(f"- {j.title} | {j.company} | {j.location or '-'} | closes {j.deadline or '?'}\n  {j.url}")


def run(args: argparse.Namespace) -> int:
    ensure_dirs()
    if args.rerank:
        from .rank import rank_pending
        with db.connect() as conn:
            n = rank_pending(conn)
        log.info("Ranked %d job(s)", n)
        return 0

    if args.dry_run:
        jobs, report = scrape(args.source)
        if not args.no_search and SETTINGS.web_search and not args.source:
            from .search import web_search
            found, _ = web_search(dry_run=True)
            jobs += filter_jobs(found)
        print(f"\n{len(jobs)} relevant job(s) (dry run, nothing saved):")
        print_jobs(jobs)
        return 0

    with db.connect() as conn:
        run_id = db.start_run(conn)
    sources_report: dict[str, Any] = {}
    new_count, state, message = 0, "ok", ""
    try:
        jobs, sources_report = scrape(args.source)
        if not args.no_search and SETTINGS.web_search and not args.source:
            from .search import web_search
            try:
                found, suggestions = web_search()
                kept = filter_jobs(found)
                jobs += kept
                sources_report["web_search"] = {"found": len(found), "kept": len(kept), "error": None}
                with db.connect() as conn:
                    for domain, url in suggestions:
                        db.add_suggestion(conn, domain, url)
            except Exception as exc:  # noqa: BLE001
                sources_report["web_search"] = {"found": 0, "kept": 0, "error": f"{type(exc).__name__}: {exc}"}
                log.exception("web search failed")

        with db.connect() as conn:
            new = db.insert_new(conn, jobs)
            new_count = len(new)
            expired = db.expire_old(conn)
        log.info("New jobs: %d (expired %d old)", new_count, expired)

        from .rank import rank_pending
        with db.connect() as conn:
            ranked = rank_pending(conn)
        log.info("Ranked %d job(s)", ranked)

        if any(r.get("error") for r in sources_report.values()):
            state = "partial"
    except Exception as exc:  # noqa: BLE001
        state, message = "failed", f"{type(exc).__name__}: {exc}"
        log.exception("Run failed")
    finally:
        with db.connect() as conn:
            db.finish_run(conn, run_id, state, sources_report, new_count, message)
    return 0 if state != "failed" else 1


def main(argv: list[str] | None = None) -> int:
    from .logging_setup import setup_logging

    p = argparse.ArgumentParser(description="Internship Job Agent pipeline")
    p.add_argument("--dry-run", action="store_true", help="scrape and print, don't save")
    p.add_argument("--source", help="run only this source (name from sources.yaml)")
    p.add_argument("--no-search", action="store_true", help="skip the Claude web-search step")
    p.add_argument("--rerank", action="store_true", help="only rank jobs that have no score yet")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    path = setup_logging(args.verbose)
    log.info("Log file: %s", path)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
