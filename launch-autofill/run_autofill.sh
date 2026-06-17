#!/bin/bash
# Daily: pre-fill empty launch + taxonomy custom fields on active Creative
# Strategist list tasks (to do / in progress / cs review / approved / sent to mb).
# Images: infer from name + description. Videos: read script from description
# or linked Google Doc; if no script anywhere, comment-ping Tomas on the task.
# Installed via launchd (com.tomas.launch-autofill.plist).
set -uo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$PATH"
export TOKEN_FILE="$HOME/.config/clickup/pk"

SCRIPT_DIR="/home/tomas/systems/launch-autofill"
LOG_DIR="$HOME/Library/Logs/launch-autofill"
mkdir -p "$LOG_DIR"
TS="$(date +%Y-%m-%d_%H%M%S)"
LOG="$LOG_DIR/$TS.log"
exec >>"$LOG" 2>&1

echo "=== launch autofill $TS ==="
[ -s "$TOKEN_FILE" ]              || { echo "ERROR: ClickUp token missing at $TOKEN_FILE"; exit 1; }
command -v python3 >/dev/null     || { echo "ERROR: python3 not on PATH"; exit 1; }
command -v claude  >/dev/null     || { echo "ERROR: claude CLI not on PATH"; exit 1; }

cd "$SCRIPT_DIR" || { echo "ERROR: cannot cd to script dir"; exit 1; }

START=$SECONDS
if python3 autofill.py; then RC=0; echo "=== done $TS ==="; else RC=$?; echo "FAILED rc=$RC"; fi
DUR=$((SECONDS - START))

# --- task-lessons capture (best-effort; never changes the job outcome) ---
if [ -f "$HOME/systems/task-lessons/lib.sh" ]; then
  # shellcheck source=/dev/null
  . "$HOME/systems/task-lessons/lib.sh"
  lessons_capture --skill "launch-autofill" --exit "$RC" --duration "$DUR" \
    --log "$LOG" --link "memory/project_launch_autofill_agent" || true
fi

exit "$RC"
