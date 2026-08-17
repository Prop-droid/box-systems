#!/usr/bin/env bash
# vtt-digest — weekly "3 viral trends + 1 suggested brief" → Tomas Pod (ClickUp chat).
# Reads the CCC /api/research/trends endpoint (the Trends tab's own data),
# drafts via headless claude, posts via chat API v3 (iteration-suggestions pattern).
# DRY_RUN=1 = draft + print, no post. Scheduled Mon 07:00 via vtt-digest.timer.
set -uo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

BASE="$HOME/systems/viral-trend-tracker"
DROPS="$BASE/digests"
LOG="$BASE/digest.log"
CHANNEL_ID="8cj5bz5-125371"          # Tomas Pod
WORKSPACE_ID="9011638245"
NOTIFY="$HOME/systems/lib/discord-notify.sh"
API="http://localhost:3000/api/research/trends"

mkdir -p "$DROPS"
[ "${DRY_RUN:-0}" = "1" ] || exec >>"$LOG" 2>&1
echo "=== [$(date)] vtt-digest run ==="

fail() {
  echo "FAIL: $1"
  "$NOTIFY" "VTT digest failed" "vtt-digest FAILED on box: $1 (see ~/systems/viral-trend-tracker/digest.log)" high || true
  exit 1
}

TODAY=$(date +%F)
[ -s "$DROPS/$TODAY.md" ] && { echo "Already dropped today — exiting"; exit 0; }

CLICKUP_TOKEN=$(cat "$HOME/.config/clickup/pk" 2>/dev/null) || fail "ClickUp token missing"
command -v claude >/dev/null || fail "claude CLI not on PATH"

DATA=$(curl -sf --max-time 30 "$API") || fail "trends API unreachable"
[ "$(printf '%s' "$DATA" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(len(d["heat"]))')" -gt 0 ] \
  || fail "trends API returned no heat data (empty-result trap)"

RAW="$DROPS/_raw.md"
WEEK=$(date +%b\ %d)
for attempt in 1 2 3; do
  { sed "s/{{WEEK}}/$WEEK/" "$BASE/digest_prompt.txt"; printf '%s' "$DATA"; } \
    | timeout 900 /usr/local/bin/claude-max --print --model claude-sonnet-4-6 \
        --dangerously-skip-permissions --allowed-tools "" > "$RAW" || true
  [ -s "$RAW" ] && grep -q "Viral trends" "$RAW" && break
  echo "attempt $attempt: invalid output, retrying"; sleep 60
done
grep -q "Viral trends" "$RAW" || fail "claude produced no valid digest after 3 attempts"

if [ "${DRY_RUN:-0}" = "1" ]; then
  echo "--- DRY_RUN draft ---"; cat "$RAW"; exit 0
fi

CLICKUP_TOKEN="$CLICKUP_TOKEN" WORKSPACE_ID="$WORKSPACE_ID" CHANNEL_ID="$CHANNEL_ID" RAW_FILE="$RAW" \
python3 - <<'PY' || fail "chat post failed"
import json, os, sys, urllib.request
tok = os.environ["CLICKUP_TOKEN"]
ws, ch = os.environ["WORKSPACE_ID"], os.environ["CHANNEL_ID"]
text = open(os.environ["RAW_FILE"]).read().strip()
i = text.find("📈")
if i > 0:
    text = text[i:]
body = json.dumps({"type": "message", "content_format": "text/md", "content": text}).encode()
req = urllib.request.Request(
    f"https://api.clickup.com/api/v3/workspaces/{ws}/chat/channels/{ch}/messages",
    data=body, method="POST",
    headers={"Authorization": tok, "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=30) as r:
    if r.status not in (200, 201):
        sys.exit(1)
    d = json.loads(r.read().decode() or "{}")
print(f"posted message id={d.get('data', {}).get('id') or d.get('id')}")
PY

cp "$RAW" "$DROPS/$TODAY.md"
echo "[$(date)] DONE: posted + saved $DROPS/$TODAY.md"
source "$HOME/systems/task-lessons/lib.sh" 2>/dev/null && lessons_capture "vtt-digest" "$LOG" || true
