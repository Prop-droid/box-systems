#!/usr/bin/env bash
set -u
. "$HOME/systems/usage-guard/config"
STATE="$HOME/.claude/usage-window.json"
PAUSE="$HOME/.claude/PAUSE_CLAUDE_BG"
FPAUSE="$HOME/fable-window/PAUSE_90"
MACSYNC_DIR="$HOME/.cache/mac-claude-projects"

# 1) best-effort pull of Mac transcripts so both machines' spend counts (shared cap)
timeout 20 rsync -a --delete -e "ssh -i ~/.ssh/id_ed25519_mac -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=accept-new" \
  tomas@100.68.166.21:~/.claude/projects/ "$MACSYNC_DIR/" 2>/dev/null || true

# 2) usage for the ACTIVE 5h block across box + mac transcripts
BLOCKS=$(CLAUDE_CONFIG_DIR="$HOME/.claude,$MACSYNC_DIR" timeout 120 npx --yes ccusage@latest blocks --json 2>/dev/null)
[ -z "$BLOCKS" ] && exit 0
read -r TOK END < <(echo "$BLOCKS" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for b in d.get('blocks',[]):
    if b.get('isActive'):
        print(b.get('totalTokens',0), b.get('endTime',''))
        break
else:
    print(0, '')" ) || true
[ -z "${TOK:-}" ] && exit 0

# 3) limit: auto = max totalTokens ever observed in a block (we hit the cap repeatedly, so max ~= cap)
if [ "$TOKEN_LIMIT" = "auto" ]; then
  LIMIT=$(echo "$BLOCKS" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(max((b.get('totalTokens',0) for b in d.get('blocks',[])), default=0))")
else
  LIMIT=$TOKEN_LIMIT
fi
[ "$LIMIT" -le 0 ] && exit 0
PCT=$(( TOK * 100 / LIMIT )); [ $PCT -gt 100 ] && PCT=100

# 4) state file (statusline reads this) + best-effort push to Mac
printf '{"pct":%d,"tokens":%d,"limit":%d,"block_end":"%s","updated":"%s"}\n' \
  "$PCT" "$TOK" "$LIMIT" "$END" "$(date -Is)" > "$STATE"
timeout 10 scp -i ~/.ssh/id_ed25519_mac -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=accept-new -q "$STATE" tomas@100.68.166.21:.claude/usage-window.json 2>/dev/null || true

H=$(date +%-H)
DAY=0; [ "$H" -ge "$DAY_START" ] && [ "$H" -lt "$DAY_END" ] && DAY=1

# 5) reset detection: block changed while paused -> clear + resume + notify
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

# 6) daytime 90% trip: pause background + alert
if [ "$DAY" -eq 1 ] && [ "$PCT" -ge "$THRESHOLD" ]; then
  echo "$END" > "$PAUSE"
  touch "$FPAUSE"
  RESET_LOCAL=$(date -d "$END" +%H:%M 2>/dev/null || echo "$END")
  MSG="90% of the 5h Claude window used (${PCT}%). Background paused; the last 10% is reserved for you. Resets ~${RESET_LOCAL}."
  curl -s -d "$MSG" -H "Title: Claude usage guard" -H "Priority: high" "$NTFY_TAB" >/dev/null
  curl -s -d "$MSG" -H "Title: Claude usage guard" -H "Priority: high" "$NTFY_PHONE" >/dev/null
fi
