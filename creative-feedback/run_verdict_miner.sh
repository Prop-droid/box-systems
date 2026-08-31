#!/bin/bash
# Daily verdict miner: Discord conversations -> creative-feedback ledger.
# Runs 04:15, ahead of the Tue 05:00 feedback synth. Honors the usage-guard
# pause via claude-max inside mine_verdicts.py.
set -uo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$PATH"

DIR="$HOME/systems/creative-feedback"
LOG_DIR="$HOME/Library/Logs/creative-feedback"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/miner-$(date +%Y-%m-%d).log"
exec >>"$LOG" 2>&1
echo "=== verdict miner $(date +%Y-%m-%d_%H%M%S) ==="

[ -f "$HOME/systems/dev-bot/.env" ] || { echo "FAIL: dev-bot .env missing (Discord token)"; exit 2; }

rc=0
timeout 1200 python3 "$DIR/mine_verdicts.py" || rc=$?
if [ "$rc" -ne 0 ]; then
  bash "$HOME/systems/lib/tg-notify.sh" "verdict-miner FAILED (rc=$rc)" \
    "Conversation->ledger mining did not run. See $LOG" || true
fi

# best-effort lesson capture, never changes rc
source "$HOME/systems/task-lessons/lib.sh" 2>/dev/null && lessons_capture --skill verdict-miner --exit "$rc" --log "$LOG" || true
exit "$rc"
