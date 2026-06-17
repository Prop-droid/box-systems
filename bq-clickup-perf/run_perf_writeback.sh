#!/bin/bash
# Nightly: write BigQuery ad performance (ROAS / Spend / Orders / Spend 30d /
# Last Active) onto active ClickUp tasks on the Creative Strategist list.
# Installed via launchd (see com.tomas.bq-clickup-perf.plist + SETUP.md).
set -uo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$PATH"
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/ejam-dwh-sa.json"
export TOKEN_FILE="$HOME/.config/clickup/pk"

SCRIPT_DIR="/home/tomas/systems/bq-clickup-perf"
LOG_DIR="$HOME/Library/Logs/bq-clickup-perf"
mkdir -p "$LOG_DIR"
TS="$(date +%Y-%m-%d_%H%M%S)"
LOG="$LOG_DIR/$TS.log"
exec >>"$LOG" 2>&1

echo "=== perf writeback $TS ==="
[ -s "$GOOGLE_APPLICATION_CREDENTIALS" ] || { echo "ERROR: BQ service account missing at $GOOGLE_APPLICATION_CREDENTIALS"; exit 1; }
[ -s "$TOKEN_FILE" ]                     || { echo "ERROR: ClickUp token missing at $TOKEN_FILE"; exit 1; }
command -v bq      >/dev/null            || { echo "ERROR: bq CLI not on PATH"; exit 1; }
command -v python3 >/dev/null            || { echo "ERROR: python3 not on PATH"; exit 1; }

cd "$SCRIPT_DIR" || { echo "ERROR: cannot cd to script dir (is Google Drive mounted?)"; exit 1; }

START=$SECONDS
if python3 bq_to_clickup_perf.py; then RC=0; echo "=== done $TS ==="; else RC=$?; echo "FAILED rc=$RC"; fi
DUR=$((SECONDS - START))

# --- task-lessons capture (best-effort; never changes the job outcome) ---
if [ -f "$HOME/systems/task-lessons/lib.sh" ]; then
  # shellcheck source=/dev/null
  . "$HOME/systems/task-lessons/lib.sh"
  lessons_capture --skill "bq-clickup-perf" --exit "$RC" --duration "$DUR" \
    --log "$LOG" --link "memory/project_bq_clickup_perf_writeback" || true
fi

exit "$RC"
