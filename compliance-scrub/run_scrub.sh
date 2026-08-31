#!/bin/bash
# Nightly compliance scrub over recently-changed copy surfaces. Deterministic
# (policy.json regex), quiet when clean, digest to #creative on hits.
set -uo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$PATH"

DIR="$HOME/systems/compliance-scrub"
LOG_DIR="$DIR/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/$(date +%Y-%m-%d).log"
exec >>"$LOG" 2>&1
echo "=== compliance scrub $(date +%F_%H%M) ==="

[ -f "$HOME/systems/compliance-eval/policy.json" ] || { echo "FAIL: policy.json missing"; exit 2; }

rc=0
timeout 600 python3 "$DIR/scan.py" || rc=$?
if [ "$rc" -ne 0 ]; then
  bash "$HOME/systems/lib/tg-notify.sh" "compliance-scrub FAILED (rc=$rc)" "See $LOG" high || true
fi
source "$HOME/systems/task-lessons/lib.sh" 2>/dev/null && lessons_capture --skill compliance-scrub --exit "$rc" --log "$LOG" || true
exit "$rc"
