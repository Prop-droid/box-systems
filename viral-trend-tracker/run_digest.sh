#!/usr/bin/env bash
# vtt-digest — weekly "3 viral trends + 1 suggested brief" → Discord #creative.
# Reads the CCC /api/research/trends endpoint (the Trends tab's own data),
# drafts via headless claude, posts via the Creative bot (launch-details-scan pattern).
# Switched from ClickUp Tomas Pod chat per Tomas 2026-08-24.
# DRY_RUN=1 = draft + print, no post. Scheduled Mon 07:00 via vtt-digest.timer.
set -uo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

BASE="$HOME/systems/viral-trend-tracker"
DROPS="$BASE/digests"
LOG="$BASE/digest.log"
DISCORD_CHANNEL_ID="1531648564932120737"   # #creative
BOTS_ENV="$HOME/agentic-os/discord/bots.env"
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

grep -q "^CREATIVE_TOKEN=." "$BOTS_ENV" 2>/dev/null || fail "CREATIVE_TOKEN missing in bots.env"
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

BOTS_ENV="$BOTS_ENV" CHANNEL_ID="$DISCORD_CHANNEL_ID" RAW_FILE="$RAW" \
python3 - <<'PY' || fail "discord post failed"
import json, os, re, sys, time, urllib.request
tok = re.search(r"^CREATIVE_TOKEN=(\S+)", open(os.environ["BOTS_ENV"]).read(), re.M).group(1)
ch = os.environ["CHANNEL_ID"]
text = open(os.environ["RAW_FILE"]).read().strip()
i = text.find("📈")
if i > 0:
    text = text[i:]
# Discord caps messages at 2000 chars — chunk on line boundaries.
chunks, cur = [], ""
for line in text.splitlines(True):
    if len(cur) + len(line) > 1900:
        chunks.append(cur); cur = ""
    cur += line
chunks.append(cur)
for n, chunk in enumerate(chunks):
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{ch}/messages",
        data=json.dumps({"content": chunk}).encode(), method="POST",
        headers={"Authorization": f"Bot {tok}", "Content-Type": "application/json",
                 # Discord 403s the default Python-urllib UA
                 "User-Agent": "vtt-digest/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode() or "{}")
    print(f"posted discord #creative message {n+1}/{len(chunks)} id={d.get('id')}")
    if n + 1 < len(chunks):
        time.sleep(1)
PY

cp "$RAW" "$DROPS/$TODAY.md"
echo "[$(date)] DONE: posted + saved $DROPS/$TODAY.md"
source "$HOME/systems/task-lessons/lib.sh" 2>/dev/null && lessons_capture "vtt-digest" "$LOG" || true
