#!/bin/bash
# One-off (scheduled for 2026-11-07 04:40 as a transient timer): restart the long-running user services that spawn
# `claude -p`, so they inherit CLAUDE_CODE_OAUTH_TOKEN from the user manager env (1-year token, 2026-11-06) before
# the old ~30-day login lapses (2026-11-09..12). Reports to the Ops Log either way.
set -u
SVCS="agentic-bots dev-bot creative-bot coach-bot ea-bot general-bot qa-bot tab-intercom"
systemctl --user show-environment | /usr/bin/grep -q '^CLAUDE_CODE_OAUTH_TOKEN=' || { "$HOME/systems/lib/tg-notify.sh" "Claude token restarts" "SKIPPED: CLAUDE_CODE_OAUTH_TOKEN is not in the user manager env" high; exit 1; }
for s in $SVCS; do systemctl --user is-enabled -q "$s" 2>/dev/null || systemctl --user is-active -q "$s" || continue; systemctl --user restart "$s"; sleep 3; done
sleep 30
ok=""; bad=""
for s in $SVCS; do
  if systemctl --user is-active -q "$s"; then
    pid=$(systemctl --user show -p MainPID --value "$s"); has=$(tr '\0' '\n' < /proc/$pid/environ 2>/dev/null | /usr/bin/grep -c '^CLAUDE_CODE_OAUTH_TOKEN=')
    ok="$ok $s(token:$has)"
  else bad="$bad $s"; fi
done
msg="Restarted for the 1-year Claude token. Up:${ok:- none}.${bad:+ DOWN:$bad}"
"$HOME/systems/lib/tg-notify.sh" "Claude token restarts" "$msg" "$([ -n "$bad" ] && echo high || echo default)"
echo "$msg"
