@echo off
rem Scrape -> filter -> dedupe -> web search -> rank. Extra args are passed through (e.g. --dry-run).
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" -m agent.main %*
