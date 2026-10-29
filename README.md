# Internship Job Agent

Finds new Sri Lankan software / QA / mobile internships twice a day, ranks them against
`profile.md` with Claude, and shows them on a local dashboard at **http://127.0.0.1:8765**.

```
scrape sources ─┐
                ├─► keyword filter ─► dedupe (SQLite) ─► rank with claude -p ─► dashboard
Claude web search┘
```

- **Scrapers** (`sources.yaml`): topjobs.lk (IT categories), itpro.lk (internships), xpress.jobs (its JSON API, IT sectors), ikman.lk (keyword searches), WSO2 and Creative Software careers pages.
- **Agent web search**: headless Claude searches the web for vacancies the scrapers miss. It also looks up companies whose career sites can't be scraped (Sysco LABS, 99x, Virtusa, IFS, …). New job sites it finds show up as **Suggested sources** on the dashboard.
- **Ranking**: `claude -p` scores each *new* job 0–100 with a one-line reason and matched skills (`prompts/rank.md`).
- **Polite**: clear User-Agent, robots.txt including `Crawl-delay`, at least 4 s between requests per site, no LinkedIn.

## Setup (Windows)

Requirements: Python 3.11+ and [Claude Code](https://claude.com/claude-code) installed and logged in (`claude` on PATH).

```powershell
cd path\to\job-agent
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env        # defaults are fine
copy profile.example.md profile.md   # then edit it with your details
.venv\Scripts\python -m pytest -q
```

Linux/macOS: the same steps with `python3 -m venv .venv`, `.venv/bin/python …` and `cp`.

## First run

```powershell
run_pipeline.bat --source topjobs --dry-run   # test one scraper, nothing saved
run_pipeline.bat                              # full run (2–4 min: scraping + web search + ranking)
start_dashboard.bat                           # opens http://127.0.0.1:8765
```

CLI flags (`python -m agent.main …`):

| Flag | What it does |
|---|---|
| `--dry-run` | Scrape + filter and print; nothing saved, no ranking |
| `--source NAME` | Only this source (name from `sources.yaml`); skips web search |
| `--no-search` | Skip the Claude web-search step (or set `WEB_SEARCH=false` in `.env`) |
| `--rerank` | Only score jobs that are still "Unranked" |

## Dashboard

- **Summary**: new since your last visit, active, closing within 7 days, applied.
- **Last run strip**: when it ran and each source's result. A red chip means that source failed; hover it to see the error.
- **Job cards** are sorted by match score. New jobs have a blue border, and jobs closing within 7 days show the deadline in red.
- **Status per job**: New → Saved → Applied → Interview → Rejected / Not interested. Notes save automatically.
- **Tabs**: All, Saved, Applied (your application tracker) and Expired. Jobs expire the day after their deadline, or 45 days after they were found if no deadline is listed.
- **Run now** runs the pipeline in the background and reloads the page when it finishes.
- **Theme** toggles light and dark mode. Your choice is remembered in this browser.

## Schedule the pipeline (8:00 and 18:00, Asia/Colombo)

**Easiest:** double-click `install_schedule.bat`. It creates all three tasks below (both pipeline runs and the dashboard at logon) and starts the dashboard. `uninstall_schedule.bat` removes them.

To do it by hand instead (your PC is on Sri Lanka time, so plain local times work), run in a normal (non-admin) terminal:

```powershell
schtasks /Create /TN "JobAgent 0800" /TR "\"C:\path\to\job-agent\run_pipeline.bat\"" /SC DAILY /ST 08:00 /F
schtasks /Create /TN "JobAgent 1800" /TR "\"C:\path\to\job-agent\run_pipeline.bat\"" /SC DAILY /ST 18:00 /F
schtasks /Query /TN "JobAgent 0800"
```

The tasks run only while you are logged in, so they use your `claude` login. If the PC was off at 8:00, open Task Scheduler → task → Properties → Settings and tick **Run task as soon as possible after a scheduled start is missed**.

Remove the tasks with `schtasks /Delete /TN "JobAgent 0800" /F` (and the same for 1800).

**cron (Linux/macOS)**: run `crontab -e` and add:

```
CRON_TZ=Asia/Colombo
0 8,18 * * * /path/to/job-agent/run_pipeline.sh >> /path/to/job-agent/logs/cron.log 2>&1
```

## Start the dashboard automatically

**Option A: start hidden at logon.** This uses `pythonw`, so no console window appears, and server output goes to `logs/dashboard.log`:

```powershell
schtasks /Create /TN "JobAgent Dashboard" /SC ONLOGON /TR "\"C:\path\to\job-agent\.venv\Scripts\pythonw.exe\" \"C:\path\to\job-agent\serve_dashboard.pyw\"" /F
```

**Option B: desktop shortcut.** Right-click `start_dashboard.bat` → Send to → Desktop (create shortcut). Double-clicking it starts the server if needed and opens the browser.

## Add a source

1. Create `agent/sources/<name>.py` with a `Source` subclass that implements `fetch() -> list[Job]` and ends with `SOURCE_CLASS = YourClass`.
2. Add an entry to `sources.yaml`.

A simple careers page needs no code: use `module: careers` with a `link_pattern` regex that matches its job URLs (see the WSO2 entry). Test it with `run_pipeline.bat --source <name> --dry-run`.

## Files

| Path | Purpose |
|---|---|
| `profile.md` | Your profile, which ranking uses (copy from `profile.example.md`; not committed). Edit it to change what ranks high. |
| `sources.yaml` | Sources, their status, and blocked domains |
| `prompts/rank.md`, `prompts/search.md` | The Claude prompts |
| `data/jobs.db` | All jobs, statuses, notes and run history (SQLite) |
| `logs/run_*.log` | One log per run, with errors per source |

## Known limits

- **topjobs.lk** adverts are images, so ranking uses the title, company and location only.
- **itpro.lk** only reads page 1 of its internships list (the newest 50), because its robots.txt disallows paging URLs. At two runs a day nothing is missed.
- **Careers pages**: Sysco LABS, 99x, Virtusa, CodeGen and Calcey render jobs with JavaScript or an external ATS. IFS and Pearson block bots. hSenid's URL is broken. All of them are covered by targeted web search.
- Each run uses two `claude -p` calls (web search, which takes 1–2 min, and ranking). Set `WEB_SEARCH=false` to save usage.
