#!/usr/bin/env bash
# Wispr call follow-ups: sync from the Mac, extract, rebuild the board.
# systemd: wispr-calls.timer. Safe to run by hand.
# A sleeping Mac is normal: keep the last data and exit 0. Fail only when the
# data is older than STALE_HOURS, or when Wispr changed its database layout.
set -uo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin"
HERE="$(cd "$(dirname "$0")" && pwd)"
BASE="${WISPR_CALLS_DIR:-$HOME/.local/share/wispr-calls}"
STALE_HOURS=100
mkdir -p "$BASE/state"
OK="$BASE/state/last_sync_ok"; FLAG="$BASE/state/schema_alerted"
log() { echo "$(date '+%Y-%m-%dT%H:%M:%S') $*"; }

out="$(bash "$HERE/sync.sh" 2>&1)"; rc=$?
if [ $rc -eq 0 ]; then
  log "sync ok: $out"; date +%s > "$OK"; rm -f "$FLAG"
elif echo "$out" | grep -q SCHEMA_CHANGED; then
  log "sync FAILED, Wispr database layout changed: $out"
  if [ ! -e "$FLAG" ]; then
    "$HOME/systems/lib/discord-notify.sh" "wispr-calls: Wispr Flow changed its database" \
      "The call sync stopped. Fix ~/systems/wispr-calls/export_mac.py. The board shows the last good data." high
    touch "$FLAG"
  fi
  exit 1
else
  log "sync skipped, Mac not reachable (rc=$rc): $(echo "$out" | tail -1)"
fi

python3 "$HERE/extract.py" && python3 "$HERE/build_board.py" || { log "extract or build FAILED"; exit 1; }

last="$(cat "$OK" 2>/dev/null || echo 0)"
age_h=$(( ( $(date +%s) - last ) / 3600 ))
if [ "$age_h" -ge "$STALE_HOURS" ]; then
  log "FAILED: no good sync for ${age_h}h (limit ${STALE_HOURS}h)"; exit 1
fi
exit 0
