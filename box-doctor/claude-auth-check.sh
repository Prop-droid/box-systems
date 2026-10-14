#!/usr/bin/env bash
# claude-auth-check — is the Max OAuth session that every headless `claude -p`
# job rides on still alive? Prints "FAIL: ..." / "WARN: ..." lines, silent when OK.
#   exit 0 = OK, 1 = FAIL (auth dead), 2 = WARN only
#   --notify  also post to #ops-log when not OK (used by the 21:30 timer, which
#             runs ahead of the 00:30-08:30 headless batch so there's time to re-login)
# box-doctor (08:45) calls it without --notify and folds the lines into its digest.
#
# 2026-10-14: the token refresh failed overnight -> mechanism-tagger + verdict-miner
# died with "OAuth session expired and could not be refreshed"; nothing warned.
set -uo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
CRED="$HOME/.claude/.credentials.json"
REFRESH_WARN_DAYS=3        # refresh token has a hard ~30d expiry; refreshes don't extend it

out=()
# 1. live probe — the only check that sees a dead refresh token
if [ -f "$HOME/.claude/PAUSE_CLAUDE_BG" ]; then
  :  # usage-guard pause: claude-max jobs are skipped anyway; don't burn a call
else
  probe="$(cd /tmp && echo 'Reply with exactly: OK' | env -u ANTHROPIC_API_KEY CLAUDE_CONFIG_DIR="$HOME/.claude" \
    timeout 120 claude -p --model claude-haiku-4-5-20251001 --no-session-persistence 2>&1)"; rc=$?
  if [ $rc -ne 0 ]; then
    if echo "$probe" | grep -qiE 'authenticat|oauth|/login|credential'; then
      out+=("FAIL: claude auth dead ($(echo "$probe" | head -1 | cut -c1-120)) — ssh box, run: claude /login")
    elif echo "$probe" | grep -qi 'usage limit'; then
      :  # window limit, transient — usage-guard owns this
    else
      out+=("WARN: claude probe rc=$rc: $(echo "$probe" | head -1 | cut -c1-120)")
    fi
  fi
fi

# 2. refresh-token cliff — warn before the hard expiry lands mid-batch
rte="$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["claudeAiOauth"].get("refreshTokenExpiresAt") or "")' "$CRED" 2>/dev/null)"
if [ -n "$rte" ]; then
  days=$(( (rte / 1000 - $(date +%s)) / 86400 ))
  [ "$days" -le "$REFRESH_WARN_DAYS" ] && \
    out+=("WARN: claude refresh token expires in ${days}d ($(date -d "@$((rte / 1000))" '+%m-%d %H:%M')) — run claude /login on the box before then")
fi

[ ${#out[@]} -eq 0 ] && exit 0
printf '%s\n' "${out[@]}"
if [ "${1:-}" = "--notify" ]; then
  prio=default; printf '%s\n' "${out[@]}" | grep -q '^FAIL' && prio=high
  "$HOME/systems/lib/tg-notify.sh" "Claude auth check" "$(printf '%s\n' "${out[@]}")" "$prio"
fi
printf '%s\n' "${out[@]}" | grep -q '^FAIL' && exit 1
exit 2
