"""SQLite storage: jobs, runs, meta, suggested sources."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

from .config import DB_PATH, SETTINGS
from .models import Job

STATUSES = ("new", "saved", "applied", "interview", "rejected", "not_interested")

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    url           TEXT NOT NULL UNIQUE,
    key_hash      TEXT NOT NULL UNIQUE,
    title         TEXT NOT NULL,
    company       TEXT NOT NULL,
    location      TEXT DEFAULT '',
    job_type      TEXT DEFAULT '',
    posted        TEXT,
    deadline      TEXT,
    description   TEXT DEFAULT '',
    source        TEXT NOT NULL,
    first_seen    TEXT NOT NULL,
    score         INTEGER,
    reason        TEXT,
    matched_skills TEXT,          -- JSON list
    status        TEXT NOT NULL DEFAULT 'new',
    notes         TEXT DEFAULT '',
    expired       INTEGER NOT NULL DEFAULT 0,
    updated_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score);
CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started     TEXT NOT NULL,
    finished    TEXT,
    state       TEXT NOT NULL DEFAULT 'running',   -- running / ok / partial / failed
    sources     TEXT,                              -- JSON {name: {found, kept, error}}
    new_count   INTEGER DEFAULT 0,
    message     TEXT
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS suggested_sources (
    domain     TEXT PRIMARY KEY,
    example_url TEXT,
    first_seen TEXT,
    hits       INTEGER DEFAULT 1
);
"""


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@contextmanager
def connect(path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ---------- dedupe ----------

def is_seen(conn: sqlite3.Connection, job: Job) -> bool:
    row = conn.execute(
        "SELECT 1 FROM jobs WHERE url = ? OR key_hash = ?", (job.url, job.key_hash)
    ).fetchone()
    return row is not None


def insert_new(conn: sqlite3.Connection, jobs: list[Job]) -> list[tuple[int, Job]]:
    """Insert unseen jobs; return (id, job) for the new ones only."""
    new: list[tuple[int, Job]] = []
    for job in jobs:
        if is_seen(conn, job):
            continue
        cur = conn.execute(
            """INSERT INTO jobs (url, key_hash, title, company, location, job_type, posted,
                                 deadline, description, source, first_seen, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (job.url, job.key_hash, job.title, job.company, job.location, job.job_type,
             job.posted, job.deadline, job.description, job.source, now(), now()),
        )
        new.append((cur.lastrowid, job))
    return new


# ---------- ranking ----------

def save_rank(conn: sqlite3.Connection, job_id: int, score: int, reason: str, skills: list[str]) -> None:
    conn.execute(
        "UPDATE jobs SET score=?, reason=?, matched_skills=?, updated_at=? WHERE id=?",
        (max(0, min(100, int(score))), reason, json.dumps(skills), now(), job_id),
    )


def unranked(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM jobs WHERE score IS NULL AND expired = 0 ORDER BY first_seen DESC"
    ).fetchall()


# ---------- expiry ----------

def expire_old(conn: sqlite3.Connection, today: date | None = None) -> int:
    """Mark jobs past deadline (or old with no deadline) as expired."""
    today = today or date.today()
    cutoff = (today - timedelta(days=SETTINGS.expire_no_deadline_days)).isoformat()
    cur = conn.execute(
        """UPDATE jobs SET expired = 1
           WHERE expired = 0 AND (
             (deadline IS NOT NULL AND deadline < ?) OR
             (deadline IS NULL AND first_seen < ?))""",
        (today.isoformat(), cutoff),
    )
    return cur.rowcount


# ---------- runs ----------

def start_run(conn: sqlite3.Connection) -> int:
    return conn.execute("INSERT INTO runs (started) VALUES (?)", (now(),)).lastrowid


def finish_run(conn: sqlite3.Connection, run_id: int, state: str, sources: dict[str, Any],
               new_count: int, message: str = "") -> None:
    conn.execute(
        "UPDATE runs SET finished=?, state=?, sources=?, new_count=?, message=? WHERE id=?",
        (now(), state, json.dumps(sources), new_count, message, run_id),
    )


def last_run(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()


# ---------- meta / suggestions ----------

def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (key, value))


def add_suggestion(conn: sqlite3.Connection, domain: str, example_url: str) -> None:
    conn.execute(
        """INSERT INTO suggested_sources (domain, example_url, first_seen) VALUES (?,?,?)
           ON CONFLICT(domain) DO UPDATE SET hits = hits + 1""",
        (domain, example_url, now()),
    )
