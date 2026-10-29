#!/usr/bin/env sh
# Start the dashboard (if not already running) and open it in the browser.
cd "$(dirname "$0")" || exit 1
PORT=$(grep -E '^DASHBOARD_PORT=' .env 2>/dev/null | cut -d= -f2 | cut -d' ' -f1)
URL="http://127.0.0.1:${PORT:-8765}"
open_url() { (command -v xdg-open >/dev/null && xdg-open "$URL") || (command -v open >/dev/null && open "$URL"); }
if curl -fs "$URL/api/run-status" >/dev/null 2>&1; then open_url; exit 0; fi
(sleep 3 && open_url) &
exec .venv/bin/python -m dashboard.app
