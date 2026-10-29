"""Local dashboard: FastAPI + Jinja2, reading data/jobs.db. Bound to 127.0.0.1 only."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from agent import db
from agent.config import LOG_DIR, ROOT, SETTINGS, ensure_dirs
from agent.deadlines import days_until

HERE = Path(__file__).resolve().parent
app = FastAPI(title="Internship Job Agent", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")

STATUS_LABELS = {
    "new": "New", "saved": "Saved", "applied": "Applied", "interview": "Interview",
    "rejected": "Rejected", "not_interested": "Not interested",
}
SORTS = {
    "score": "score IS NULL, score DESC, first_seen DESC",
    "deadline": "deadline IS NULL, deadline ASC",
    "found": "first_seen DESC",
}
TABS = {
    "all": "expired = 0 AND status NOT IN ('not_interested','rejected')",
    "saved": "expired = 0 AND status = 'saved'",
    "applied": "status IN ('applied','interview','rejected')",
    "expired": "expired = 1",
}
STALE_RUN = timedelta(minutes=45)
_proc: subprocess.Popen | None = None


def _visit_marker(conn) -> str:
    """'New since last visit' cutoff. A visit counts after 30 min away, so reloads keep highlights."""
    now = datetime.now()
    last = db.get_meta(conn, "last_visit_at")
    prev = db.get_meta(conn, "prev_visit_at") or last or "1970-01-01T00:00:00"
    if not last or now - datetime.fromisoformat(last) > timedelta(minutes=30):
        prev = last or "1970-01-01T00:00:00"
        db.set_meta(conn, "prev_visit_at", prev)
    db.set_meta(conn, "last_visit_at", now.isoformat(timespec="seconds"))
    return prev


def _enrich(row, since: str) -> dict[str, Any]:
    d = dict(row)
    d["skills"] = json.loads(d.get("matched_skills") or "[]")
    d["days_left"] = days_until(d.get("deadline"))
    d["closing_soon"] = d["days_left"] is not None and 0 <= d["days_left"] <= 7
    d["is_new"] = d["first_seen"] > since
    return d


def _run_info(conn) -> dict[str, Any] | None:
    row = db.last_run(conn)
    if not row:
        return None
    d = dict(row)
    d["sources"] = json.loads(d.get("sources") or "{}")
    running = d["state"] == "running" and datetime.now() - datetime.fromisoformat(d["started"]) < STALE_RUN
    d["running"] = running or (_proc is not None and _proc.poll() is None)
    if d["state"] == "running" and not d["running"]:
        d["state"] = "failed"
        d["message"] = d.get("message") or "Run did not finish (stopped or crashed)."
    return d


def _page(request: Request, tab: str, q: str = "", source: str = "", min_score: int | None = None,
          location: str = "", status: str = "", sort: str = "score") -> HTMLResponse:
    ensure_dirs()
    where, params = [TABS[tab]], []
    if q:
        where.append("(title LIKE ? OR company LIKE ? OR description LIKE ? OR reason LIKE ?)")
        params += [f"%{q}%"] * 4
    if source:
        where.append("source = ?")
        params.append(source)
    if min_score is not None:
        where.append("score >= ?")
        params.append(min_score)
    if location:
        where.append("location LIKE ?")
        params.append(f"%{location}%")
    if status:
        where.append("status = ?")
        params.append(status)
    order = SORTS.get(sort, SORTS["score"])
    today = date.today().isoformat()
    soon = (date.today() + timedelta(days=7)).isoformat()
    with db.connect() as conn:
        db.expire_old(conn)
        since = _visit_marker(conn) if tab == "all" else (db.get_meta(conn, "prev_visit_at") or "")
        rows = conn.execute(f"SELECT * FROM jobs WHERE {' AND '.join(where)} ORDER BY {order}", params).fetchall()
        q1 = lambda sql, *a: conn.execute(sql, a).fetchone()[0]  # noqa: E731
        stats = {
            "new": q1("SELECT COUNT(*) FROM jobs WHERE expired=0 AND first_seen > ?", since),
            "active": q1("SELECT COUNT(*) FROM jobs WHERE expired=0 AND status NOT IN ('not_interested','rejected')"),
            "closing": q1("SELECT COUNT(*) FROM jobs WHERE expired=0 AND deadline BETWEEN ? AND ? "
                          "AND status NOT IN ('not_interested','rejected')", today, soon),
            "applied": q1("SELECT COUNT(*) FROM jobs WHERE status IN ('applied','interview')"),
            "unranked": q1("SELECT COUNT(*) FROM jobs WHERE score IS NULL AND expired=0"),
        }
        counts = {t: q1(f"SELECT COUNT(*) FROM jobs WHERE {w}") for t, w in TABS.items()}
        sources = [r[0] for r in conn.execute("SELECT DISTINCT source FROM jobs ORDER BY source")]
        suggestions = conn.execute("SELECT * FROM suggested_sources ORDER BY hits DESC LIMIT 8").fetchall()
        run = _run_info(conn)
    return templates.TemplateResponse(request, "index.html", {
        "tab": tab, "jobs": [_enrich(r, since) for r in rows], "stats": stats, "counts": counts,
        "run": run, "sources": sources, "suggestions": suggestions, "statuses": STATUS_LABELS,
        "f": {"q": q, "source": source, "min_score": min_score, "location": location,
              "status": status, "sort": sort},
        "filtered": any([q, source, min_score is not None, location, status]),
    })


@app.get("/", response_class=HTMLResponse)
def home(request: Request, q: str = "", source: str = "", min_score: int | None = None,
         location: str = "", status: str = "", sort: str = "score"):
    return _page(request, "all", q, source, min_score, location, status, sort)


@app.get("/{tab}", response_class=HTMLResponse)
def tab_page(request: Request, tab: str, q: str = "", source: str = "", min_score: int | None = None,
             location: str = "", status: str = "", sort: str = "score"):
    if tab not in TABS or tab == "all":
        raise HTTPException(404)
    return _page(request, tab, q, source, min_score, location, status, sort)


class JobUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None


@app.post("/jobs/{job_id}")
def update_job(job_id: int, body: JobUpdate) -> JSONResponse:
    if body.status is not None and body.status not in STATUS_LABELS:
        raise HTTPException(400, "bad status")
    with db.connect() as conn:
        if body.status is not None:
            conn.execute("UPDATE jobs SET status=?, updated_at=? WHERE id=?", (body.status, db.now(), job_id))
        if body.notes is not None:
            conn.execute("UPDATE jobs SET notes=?, updated_at=? WHERE id=?", (body.notes[:5000], db.now(), job_id))
    return JSONResponse({"ok": True})


def _spawn(*args: str) -> None:
    global _proc
    with db.connect() as conn:
        info = _run_info(conn)
    if info and info["running"]:
        raise HTTPException(409, "A run is already in progress")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    out = open(LOG_DIR / "dashboard_run.out", "w", encoding="utf-8")  # noqa: SIM115 - child owns it
    _proc = subprocess.Popen([sys.executable, "-m", "agent.main", *args], cwd=ROOT,
                             stdout=out, stderr=subprocess.STDOUT, creationflags=flags)


@app.post("/run")
def run_now() -> JSONResponse:
    _spawn()
    return JSONResponse({"started": True})


@app.post("/rerank")
def rerank() -> JSONResponse:
    _spawn("--rerank")
    return JSONResponse({"started": True})


@app.get("/api/run-status")
def run_status() -> JSONResponse:
    with db.connect() as conn:
        info = _run_info(conn)
    running = bool(info and info["running"]) or (_proc is not None and _proc.poll() is None)
    return JSONResponse({"running": running, "run": info})


def main() -> None:
    import uvicorn

    uvicorn.run(app, host=SETTINGS.dashboard_host, port=SETTINGS.dashboard_port, log_level="warning")


if __name__ == "__main__":
    main()
