#!/bin/bash
# Weekly wiki -> eJam Company Brain sync.
# Rebuilds the export from the current wiki (prepare.py) and pushes it
# (push.py — idempotent: existing slugs become update_entry calls).
# On any failure, notify the phone via ntfy and exit nonzero.
set -uo pipefail
PKG="$HOME/brain/exports/2026-07_ejam-brain-wiki-push"
LOG="$HOME/systems/brain-push/last_run.log"
NTFY_TOPIC="tomas-ph-1ea8ac8e"

{
  echo "=== brain-push $(date -Is) ==="
  cd "$PKG" || exit 1
  python3 prepare.py && python3 push.py
} >"$LOG" 2>&1

rc=$?
if [ $rc -ne 0 ] || grep -qE "FAIL|NO WRITE GRANT" "$LOG"; then
  tail -5 "$LOG" | curl -s -H "Title: brain-push failed" -d @- "https://ntfy.sh/$NTFY_TOPIC" >/dev/null
  echo "brain-push FAILED (rc=$rc) — see $LOG"
  exit 1
fi
echo "brain-push ok — $(grep -c '^  ok ' "$LOG") entries"
