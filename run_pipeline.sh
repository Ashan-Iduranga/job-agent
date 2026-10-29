#!/usr/bin/env sh
# Scrape -> filter -> dedupe -> web search -> rank. Extra args are passed through (e.g. --dry-run).
cd "$(dirname "$0")" || exit 1
export PYTHONIOENCODING=utf-8
exec .venv/bin/python -m agent.main "$@"
