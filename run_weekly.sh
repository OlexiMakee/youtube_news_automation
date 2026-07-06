#!/bin/bash
# Weekly update: scrape all channels (7 days) + analytics + launch dashboard
#
# Pass --no-dashboard (or set RUN_WEEKLY_NO_DASHBOARD=1) to stop after the data
# refresh and skip launching the Flask dev server. Use this for headless/remote
# callers (e.g. a cloud agent) that just need fresh data and would otherwise
# hang on the blocking dashboard process.
set -e
cd "$(dirname "$0")"

NO_DASHBOARD=0
if [ "$1" = "--no-dashboard" ] || [ "$RUN_WEEKLY_NO_DASHBOARD" = "1" ]; then
  NO_DASHBOARD=1
fi

PYTHON="venv_auto/bin/python3.9"
if ! [ -f "$PYTHON" ]; then
  PYTHON=$(which python3)
fi

echo "=== [1/3] Scraping all channels (last 7 days) ==="
$PYTHON scrape_multi.py --days 7 --no-prompt

echo ""
echo "=== [2/3] Analytics: trends + top videos (last 7 days) ==="
$PYTHON scripts/analytics_engine.py trends --days 7 2>/dev/null || echo "(trends unavailable)"
$PYTHON scripts/analytics_engine.py top --days 7 2>/dev/null || echo "(top unavailable)"

if [ "$NO_DASHBOARD" = "1" ]; then
  echo ""
  echo "=== Done (dashboard launch skipped, --no-dashboard) ==="
  exit 0
fi

echo ""
echo "=== [3/3] Launching dashboard at http://127.0.0.1:5001 ==="
$PYTHON web_app.py
