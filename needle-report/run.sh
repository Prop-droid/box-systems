#!/usr/bin/env bash
# Run the wiki needle-test harness and post the TL;DR to Discord #ops-log.
# Usage: run.sh [extra run.py args, e.g. --fresh --only fiber-grams]
# The harness itself (guard.py: minimal MCP, loadavg gate, checkpoints) lives in
# ~/brain/systems/needle-test — this is just the run+notify wrapper.
set -u
export PATH="$HOME/.local/bin:$PATH"   # timers/cron get no login env; run.py execs `claude`
NT="$HOME/brain/systems/needle-test"
LOG="$HOME/systems/needle-report/last_run.log"
NOTIFY="$HOME/systems/lib/tg-notify.sh"

cd "$NT" || exit 1
python3 run.py "$@" >"$LOG" 2>&1
rc=$?

rep="$NT/report-$(date +%F).md"
if [ -f "$rep" ]; then
  summary="$(sed -n 2p "$rep")"
  fails="$(awk -F'|' '$3 ~ /FAIL/ {gsub(/ /,"",$2); print $2}' "$rep" | paste -sd', ' -)"
  if [ -n "$fails" ]; then prio=high; else prio=low; fi
  "$NOTIFY" "Needle test $(date +%F)" "$summary
Failing: ${fails:-none}
Report: $rep" "$prio"
else
  "$NOTIFY" "Needle test $(date +%F) produced no report (rc=$rc)" "log: $LOG" high
  exit 1
fi
