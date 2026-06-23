#!/bin/bash
# Weekly update: scrape all channels (7 days) + analytics + launch dashboard
set -e
cd "$(dirname "$0")"

PYTHON="venv_auto/bin/python3.9"
if ! [ -f "$PYTHON" ]; then
  PYTHON=$(which python3)
fi

echo "=== [1/3] Scraping all channels (last 7 days) ==="
$PYTHON scrape_multi.py --days 7

echo ""
echo "=== [2/3] Analytics: trends + top videos (last 7 days) ==="
$PYTHON scripts/analytics_engine.py trends --days 7 2>/dev/null || echo "(trends unavailable)"
$PYTHON scripts/analytics_engine.py top --days 7 2>/dev/null || echo "(top unavailable)"

echo ""
echo "=== [3/3] Launching dashboard at http://127.0.0.1:5001 ==="
$PYTHON web_app.py
