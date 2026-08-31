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
NOTIFY="$HOME/systems/lib/tg-notify.sh"
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

grep -q "^TELEGRAM_TOKEN=." "$HOME/systems/tg-creative-bot/.env" 2>/dev/null || fail "TELEGRAM_TOKEN missing in tg-creative-bot/.env"
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

# Telegram-only rule (2026-08-31): digest goes to the Creative Feed topic.
TRIMMED="$(mktemp)"
python3 - "$RAW" > "$TRIMMED" <<'PY'
import sys
text = open(sys.argv[1]).read().strip()
i = text.find("📈")
print(text[i:] if i > 0 else text)
PY
bash "$HOME/systems/lib/tg-post.sh" "📊 Creative Feed" tg-creative-bot "$TRIMMED" || fail "telegram post failed"
rm -f "$TRIMMED"

cp "$RAW" "$DROPS/$TODAY.md"
echo "[$(date)] DONE: posted + saved $DROPS/$TODAY.md"
source "$HOME/systems/task-lessons/lib.sh" 2>/dev/null && lessons_capture "vtt-digest" "$LOG" || true
