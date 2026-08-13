#!/bin/bash
# Weekly skill/tool telemetry: refresh staged Mac transcripts, scan box + Mac,
# write a dated report the self-improve digest picks up. Deterministic, no LLM.
set -uo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$PATH"
DIR="$HOME/systems/skill-telemetry"
LOG_DIR="$DIR/logs"; mkdir -p "$LOG_DIR" "$DIR/reports"
TS="$(date +%Y-%m-%d)"
exec >>"$LOG_DIR/run-$TS.log" 2>&1
echo "=== skill-telemetry $TS ==="

# Reuse correction-capture's Mac pull so telemetry sees Mac sessions too (best-effort).
[ -x "$HOME/systems/correction-capture/pull_mac.sh" ] && bash "$HOME/systems/correction-capture/pull_mac.sh" || true

python3 "$DIR/telemetry.py" --days 30 --out "$DIR/reports/$TS.md" || { echo "FAILED"; exit 1; }
echo "=== done $TS -> reports/$TS.md ==="
