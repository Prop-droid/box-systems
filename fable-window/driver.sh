#!/usr/bin/env bash
# fable-window driver v2: sequential headless claude runs, model-routed per task.
# v2: usage-limit hits pause and retry (30 min, max 16 tries) instead of failing forward.
set -u
B="$HOME/fable-window"; CL="$HOME/.local/bin/claude"
NTFY="https://ntfy.sh/tomas-tab-958e4431"
START_AT="${START_AT:-}"
if [ -n "$START_AT" ] && [ ! -f "$B/START_NOW" ]; then
  target=$(date -d "today $START_AT" +%s)
  [ "$(date +%s)" -gt "$target" ] && target=$(date -d "tomorrow $START_AT" +%s)
  echo "waiting until $(date -d @$target) (touch $B/START_NOW to begin immediately)"
  while [ "$(date +%s)" -lt "$target" ] && [ ! -f "$B/START_NOW" ]; do sleep 60; done
fi
curl -s -d "Fable run STARTING" -H "Title: Fable window" "$NTFY" >/dev/null
for t in "$B"/tasks/*.task; do
  [ -f "$B/STOP" ] && { echo "STOP file present, aborting"; break; }
  name=$(basename "$t" .task)
  while [ -f "$B/PAUSE_90" ]; do sleep 300; done
  [ -f "$B/logs/$name.done" ] && continue
  model=$(sed -n 's/^MODEL: //p;1q' "$t")
  cwd=$(sed -n '2{s/^CWD: //p}' "$t"); cwd="${cwd/#\~/$HOME}"
  prompt=$(tail -n +4 "$t")
  tries=0
  while :; do
    [ -f "$B/STOP" ] && break 2
    echo "=== $(date +%F\ %H:%M) running $name (model=$model try=$tries) ==="
    ( cd "$cwd" && timeout 3600 "$CL" -p "$prompt" --model "$model" --dangerously-skip-permissions < /dev/null ) \
        > "$B/logs/$name.log" 2>&1
    rc=$?
    if [ $rc -ne 0 ] && grep -qiE "session limit|usage limit|rate limit|credit balance" "$B/logs/$name.log"; then
      tries=$((tries+1))
      if [ $tries -ge 16 ]; then
        echo "exit=$rc LIMIT-GAVE-UP $(date -Is)" > "$B/logs/$name.done"
        curl -s -d "fable: $name gave up after 16 limit-retries" "$NTFY" >/dev/null
        break
      fi
      curl -s -d "fable: usage limit hit on $name, sleeping 30m (try $tries/16)" "$NTFY" >/dev/null
      sleep 1800
      continue
    fi
    echo "exit=$rc $(date -Is)" > "$B/logs/$name.done"
    curl -s -d "fable: $name done (exit=$rc)" "$NTFY" >/dev/null
    break
  done
done
curl -s -d "Fable run COMPLETE (or stopped). See ~/fable-window/REPORT.md" -H "Title: Fable window" "$NTFY" >/dev/null
