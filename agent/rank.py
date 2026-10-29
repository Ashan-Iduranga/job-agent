"""Score unranked jobs against profile.md with headless Claude, in batches."""
from __future__ import annotations

import json
import logging
import sqlite3

from . import db
from .claude_cli import ClaudeError, run_claude
from .config import DATA_DIR, PROMPTS_DIR, SETTINGS

log = logging.getLogger(__name__)

NEW_JOBS = DATA_DIR / "new_jobs.json"
RANKED = DATA_DIR / "ranked.json"


def _job_payload(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "title": row["title"], "company": row["company"],
        "location": row["location"], "job_type": row["job_type"], "deadline": row["deadline"],
        "source": row["source"], "description": (row["description"] or "")[:1500],
    }


def rank_batch(conn: sqlite3.Connection, rows: list[sqlite3.Row]) -> int:
    """Rank one batch; returns how many jobs got a score."""
    NEW_JOBS.write_text(json.dumps([_job_payload(r) for r in rows], indent=2, ensure_ascii=False), encoding="utf-8")
    RANKED.unlink(missing_ok=True)
    run_claude((PROMPTS_DIR / "rank.md").read_text(encoding="utf-8"), "Read,Write")
    if not RANKED.exists():
        raise ClaudeError("claude did not write data/ranked.json")
    results = json.loads(RANKED.read_text(encoding="utf-8"))
    ids = {r["id"] for r in rows}
    n = 0
    for item in results:
        if item.get("id") in ids and isinstance(item.get("score"), (int, float)):
            db.save_rank(conn, item["id"], item["score"], str(item.get("reason", ""))[:300],
                         [str(s) for s in item.get("matched_skills", [])][:15])
            n += 1
    conn.commit()
    return n


def rank_pending(conn: sqlite3.Connection) -> int:
    """Rank every job without a score. A failed batch is left unranked for the next run."""
    rows = db.unranked(conn)
    size = max(1, SETTINGS.rank_batch_size)
    total = 0
    for i in range(0, len(rows), size):
        batch = rows[i:i + size]
        try:
            total += rank_batch(conn, batch)
        except (ClaudeError, json.JSONDecodeError, OSError) as exc:
            log.error("Ranking batch %d failed: %s (jobs stay 'Unranked')", i // size + 1, exc)
    return total
