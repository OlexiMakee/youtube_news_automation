#!/bin/bash
# Weekly update: scrape channels (7 days) + analytics + optional dashboard
#
# Pass --no-dashboard (or set RUN_WEEKLY_NO_DASHBOARD=1) to stop after the data
# refresh and skip launching the Flask dev server. Use this for headless/remote
# callers (e.g. a cloud agent) that just need fresh data and would otherwise
# hang on the blocking dashboard process.
# Pass --profile english for UATV English editorial automation. This avoids
# profile-only monitoring sets such as Hungary.
set -e
cd "$(dirname "$0")"

NO_DASHBOARD=0
PROFILE="${RUN_WEEKLY_PROFILE:-}"
SCRAPE_ARGS=(--days 7 --no-prompt)

while [ "$#" -gt 0 ]; do
  case "$1" in
    --no-dashboard)
      NO_DASHBOARD=1
      ;;
    --profile)
      shift
      PROFILE="${1:-}"
      ;;
    --profile=*)
      PROFILE="${1#--profile=}"
      ;;
    --no-cloud-sync)
      SCRAPE_ARGS+=(--no-cloud-sync)
      ;;
    --skip-postgres-sync)
      SCRAPE_ARGS+=(--skip-postgres-sync)
      ;;
    *)
      echo "[!] Unknown option: $1" >&2
      exit 2
      ;;
  esac
  shift
done

if [ "$RUN_WEEKLY_NO_DASHBOARD" = "1" ] || [ ! -t 1 ]; then
  NO_DASHBOARD=1
fi

if [ -n "$PROFILE" ]; then
  SCRAPE_ARGS+=(--profile "$PROFILE")
fi

PYTHON="venv_auto/bin/python3.9"
if ! [ -f "$PYTHON" ]; then
  PYTHON=$(which python3)
fi

if [ -n "$PROFILE" ]; then
  echo "=== [1/3] Scraping '$PROFILE' profile (last 7 days) ==="
else
  echo "=== [1/3] Scraping default channels (last 7 days) ==="
fi
$PYTHON scrape_multi.py "${SCRAPE_ARGS[@]}"

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
