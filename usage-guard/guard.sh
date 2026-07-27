#!/usr/bin/env bash
set -u
. "$HOME/systems/usage-guard/config"
STATE="$HOME/.claude/usage-window.json"
PAUSE="$HOME/.claude/PAUSE_CLAUDE_BG"
FPAUSE="$HOME/fable-window/PAUSE_90"
MACSYNC_DIR="$HOME/.cache/mac-claude-projects"

# 1) PRIMARY: exact utilization from Anthropic's OAuth usage endpoint — the same
#    numbers the /usage screen shows. Server-side, so Mac spend counts even while
#    the Mac sleeps. Token comes from Claude Code's own credentials file and is
#    kept fresh by normal claude usage on the box.
PCT=""; END=""; TOKENS=0; LIMIT=0; WEEK=""; SRC="oauth"
ATOK=$(python3 -c "import json;print(json.load(open('$HOME/.claude/.credentials.json'))['claudeAiOauth']['accessToken'])" 2>/dev/null || true)
if [ -n "$ATOK" ]; then
  RESP=$(curl -s -m 15 "https://api.anthropic.com/api/oauth/usage" \
    -H "Authorization: Bearer $ATOK" -H "anthropic-beta: oauth-2025-04-20" 2>/dev/null || true)
  read -r PCT END WEEK < <(echo "$RESP" | python3 -c "
import json,sys
try:
    d = json.load(sys.stdin)
    f = d['five_hour']
    w = d.get('seven_day') or {}
    print(int(round(f['utilization'])), f['resets_at'][:19], int(round(w.get('utilization') or 0)))
except Exception:
    pass") || true
fi

# 2) FALLBACK: ccusage token estimate over box+mac transcripts (old behavior).
#    TOKEN_LIMIT in config only matters on this path.
if [ -z "${PCT:-}" ] || [ -z "${END:-}" ]; then
  SRC="ccusage"
  timeout 20 rsync -a --delete -e "ssh -i ~/.ssh/id_ed25519_mac -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=accept-new" \
    tomas@100.68.166.21:~/.claude/projects/ "$MACSYNC_DIR/" 2>/dev/null || true
  BLOCKS=$(CLAUDE_CONFIG_DIR="$HOME/.claude,$MACSYNC_DIR" timeout 120 npx --yes ccusage@latest blocks --json 2>/dev/null)
  [ -z "$BLOCKS" ] && exit 0
  read -r TOKENS END < <(echo "$BLOCKS" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for b in d.get('blocks',[]):
    if b.get('isActive'):
        print(b.get('totalTokens',0), b.get('endTime',''))
        break
else:
    print(0, '')" ) || true
  [ -z "${TOKENS:-}" ] && exit 0
  LIMIT=$TOKEN_LIMIT
  [ "$LIMIT" -le 0 ] && exit 0
  PCT=$(( TOKENS * 100 / LIMIT )); [ $PCT -gt 100 ] && PCT=100
  WEEK=""
fi

# 3) state file (statusline reads this) + best-effort push to Mac
printf '{"pct":%d,"tokens":%d,"limit":%d,"week_pct":%s,"source":"%s","block_end":"%s","updated":"%s"}\n' \
  "$PCT" "$TOKENS" "$LIMIT" "${WEEK:-null}" "$SRC" "$END" "$(date -Is)" > "$STATE"
timeout 10 scp -i ~/.ssh/id_ed25519_mac -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=accept-new -q "$STATE" tomas@100.68.166.21:.claude/usage-window.json 2>/dev/null || true

H=$(date +%-H)
DAY=0; [ "$H" -ge "$DAY_START" ] && [ "$H" -lt "$DAY_END" ] && DAY=1

# 4) reset detection: window changed while paused -> clear + resume + notify
if [ -f "$PAUSE" ]; then
  OLDEND=$(cat "$PAUSE")
  if [ "$END" != "$OLDEND" ]; then
    rm -f "$PAUSE" "$FPAUSE"
    systemctl --user start fable-resume.service 2>/dev/null
    for N in "$NTFY_TAB" "$NTFY_PHONE"; do
      curl -s -d "Usage window reset. Background work resumed automatically." -H "Title: Usage guard" "$N" >/dev/null
    done
  fi
  exit 0
fi

# 5) daytime 90% trip: pause background + alert
if [ "$DAY" -eq 1 ] && [ "$PCT" -ge "$THRESHOLD" ]; then
  echo "$END" > "$PAUSE"
  touch "$FPAUSE"
  RESET_LOCAL=$(date -d "$END" +%H:%M 2>/dev/null || echo "$END")
  MSG="90% of the 5h Claude window used (${PCT}%, source: ${SRC}). Background paused; the last 10% is reserved for you. Resets ~${RESET_LOCAL}."
  curl -s -d "$MSG" -H "Title: Claude usage guard" -H "Priority: high" "$NTFY_TAB" >/dev/null
  curl -s -d "$MSG" -H "Title: Claude usage guard" -H "Priority: high" "$NTFY_PHONE" >/dev/null
fi
