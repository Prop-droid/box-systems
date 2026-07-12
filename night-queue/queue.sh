#!/usr/bin/env bash
# night-queue driver v3: sequential headless claude runs, model-routed per task.
# Permanent, generic successor to ~/fable-window/driver.sh (v2). Changes vs v2:
#   - header parsing by key (MODEL/CWD/TIMEOUT in any order), not line position
#   - per-task TIMEOUT (default 3600s)
#   - limit-retry regex extended with Fable-era wording (weekly/5-hour limit, resets at)
#   - honors ~/.claude/PAUSE_CLAUDE_BG + queue-local PAUSE/PAUSE_90 mid-loop
#   - auto git-commits queue/artifacts + queue/tasks on completion
# Queue dir override: NQ_DIR=/path bash queue.sh (default ~/systems/night-queue/queue)
set -u
NQ_HOME="$HOME/systems/night-queue"
Q="${NQ_DIR:-$NQ_HOME/queue}"
CL="$HOME/.local/bin/claude"
NTFY="https://ntfy.sh/${NQ_NTFY:-tomas-tab-958e4431}"
LIMIT_RE="session limit|usage limit|rate limit|credit balance|reached your .*limit|usage-credits|limit (reached|hit)|hit your .*limit|5-hour limit|weekly limit|fable.*limit|resets at [0-9]"

ntfy() { curl -sm 10 -d "$1" -H "Title: night-queue" "$NTFY" >/dev/null || true; }
paused() { [ -f "$HOME/.claude/PAUSE_CLAUDE_BG" ] || [ -f "$Q/PAUSE" ] || [ -f "$Q/PAUSE_90" ]; }

mkdir -p "$Q/tasks" "$Q/logs" "$Q/artifacts"

# double-launch guard: another queue.sh already alive (anchored pattern; excludes self)
if pgrep -f "^bash $NQ_HOME/queue.sh" | grep -qv "^$$\$"; then
  echo "another queue.sh is running, exiting"; exit 0
fi

# optional delayed start: START_AT=23:00 bash queue.sh ; touch $Q/START_NOW to begin now
START_AT="${START_AT:-}"
if [ -n "$START_AT" ] && [ ! -f "$Q/START_NOW" ]; then
  target=$(date -d "today $START_AT" +%s)
  [ "$(date +%s)" -gt "$target" ] && target=$(date -d "tomorrow $START_AT" +%s)
  echo "waiting until $(date -d @"$target") (touch $Q/START_NOW to begin immediately)"
  while [ "$(date +%s)" -lt "$target" ] && [ ! -f "$Q/START_NOW" ]; do sleep 60; done
fi

shopt -s nullglob
tasks=("$Q"/tasks/*.task)
[ ${#tasks[@]} -eq 0 ] && { echo "no tasks in $Q/tasks"; exit 0; }

ntfy "queue STARTING (${#tasks[@]} tasks)"
for t in "${tasks[@]}"; do
  [ -f "$Q/STOP" ] && { echo "STOP file present, aborting"; break; }
  name=$(basename "$t" .task)
  [ -f "$Q/logs/$name.done" ] && continue
  while paused; do [ -f "$Q/STOP" ] && break 2; sleep 300; done
  model=$(sed -n 's/^MODEL: //p' "$t" | head -1); : "${model:=claude-sonnet-4-6}"
  cwd=$(sed -n 's/^CWD: //p' "$t" | head -1); cwd="${cwd/#\~/$HOME}"; : "${cwd:=$HOME}"
  tmo=$(sed -n 's/^TIMEOUT: //p' "$t" | head -1); : "${tmo:=3600}"
  prompt=$(awk 'flag; /^$/{flag=1}' "$t")
  tries=0
  while :; do
    [ -f "$Q/STOP" ] && break 2
    echo "=== $(date +%F\ %H:%M) running $name (model=$model timeout=$tmo try=$tries) ==="
    ( cd "$cwd" && timeout "$tmo" "$CL" -p "$prompt" --model "$model" --dangerously-skip-permissions < /dev/null ) \
        > "$Q/logs/$name.log" 2>&1
    rc=$?
    if [ $rc -ne 0 ] && grep -qiE "$LIMIT_RE" "$Q/logs/$name.log"; then
      tries=$((tries+1))
      if [ $tries -ge 16 ]; then
        echo "exit=$rc LIMIT-GAVE-UP $(date -Is)" > "$Q/logs/$name.done"
        ntfy "$name gave up after 16 limit-retries"
        break
      fi
      ntfy "usage limit on $name, sleeping 30m (try $tries/16)"
      sleep 1800
      continue
    fi
    echo "exit=$rc $(date -Is)" > "$Q/logs/$name.done"
    ntfy "$name done (exit=$rc)"
    break
  done
done

# auto-commit artifacts + task defs if the queue dir lives in a git repo
if git -C "$Q" rev-parse --git-dir >/dev/null 2>&1; then
  git -C "$Q" add -A "$Q/artifacts" "$Q/tasks" 2>/dev/null
  git -C "$Q" diff --cached --quiet -- "$Q/artifacts" "$Q/tasks" \
    || git -C "$Q" commit -q -m "night-queue: run artifacts $(date +%F)" -- "$Q/artifacts" "$Q/tasks" \
    || true
fi

ntfy "queue COMPLETE (or stopped). nq status for details"
