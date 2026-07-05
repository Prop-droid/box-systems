#!/bin/bash
# Creative fatigue sentinel — daily wrapper for fatigue_sentinel.py.
# Alerts (ntfy) when a winning ad's hook rate or ROAS decays vs its 7-day
# baseline. Scheduled via systemd user timer (see systemd/*.service|*.timer),
# NOT launchd. Staging only until enabled via ~/systems/systemd/install.sh.
set -uo pipefail

export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$PATH"
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/ejam-dwh-sa.json"
export NTFY_TOPIC="${NTFY_TOPIC:-tomas-tab-958e4431}"

SCRIPT_DIR="$HOME/systems/fatigue-sentinel"
cd "$SCRIPT_DIR" || { echo "ERROR: cannot cd to $SCRIPT_DIR"; exit 1; }

[ -s "$GOOGLE_APPLICATION_CREDENTIALS" ] || { echo "ERROR: BQ service account missing at $GOOGLE_APPLICATION_CREDENTIALS"; exit 1; }
command -v bq      >/dev/null || { echo "ERROR: bq CLI not on PATH"; exit 1; }
command -v python3 >/dev/null || { echo "ERROR: python3 not on PATH"; exit 1; }

# In --dry-run, keep output on stdout (so it can be inspected/captured).
# Live runs log to a dated file under logs/.
if [[ "$*" == *--dry-run* ]]; then
  exec python3 fatigue_sentinel.py "$@"
fi

LOG_DIR="$SCRIPT_DIR/logs"; mkdir -p "$LOG_DIR"
TS="$(date +%Y-%m-%d_%H%M%S)"
LOG="$LOG_DIR/$TS.log"
exec >>"$LOG" 2>&1

echo "=== fatigue sentinel $TS ==="
if python3 fatigue_sentinel.py "$@"; then RC=0; echo "=== done $TS ==="; else RC=$?; echo "FAILED rc=$RC"; fi
exit "$RC"
