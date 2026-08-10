#!/usr/bin/env bash
# Monthly tax reminder — fires on the 27th of every month (systemd timer is the
# recurrence; the Google Tasks API cannot set recurrence itself) and inserts a
# "Do the taxes" task, due that day, on the personal PERSONAL Google Tasks list.
# create_task.py is idempotent, so a Persistent=true catch-up run is safe.
# ntfy fires only on FAILURE — the task itself is the reminder.
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$DIR/run.log"
PY="/home/tomas/tablet-assistant/venv/bin/python"
NTFY_TOPIC="tomas-ph-1ea8ac8e"

ts="$(date '+%F %T')"
if out="$("$PY" "$DIR/create_task.py" 2>&1)"; then
  echo "$ts $out" >> "$LOG"
else
  echo "$ts FAILED: $out" >> "$LOG"
  curl -s -m 15 -H "Title: Tax task NOT created" -H "Priority: high" -H "Tags: warning" \
    -d "Google Tasks insert failed on $(hostname -s): $(echo "$out" | tail -3)" \
    "https://ntfy.sh/$NTFY_TOPIC" >/dev/null 2>&1
  exit 1
fi
