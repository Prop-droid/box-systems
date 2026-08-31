#!/usr/bin/env bash
# TELEGRAM-ONLY RULE (Tomas 2026-08-31): all box alerts go to the Telegram
# 🔔 Ops Log topic via tg-notify.sh. This shim keeps every existing caller
# working unchanged. Original Discord webhook body kept below for rollback.
TITLE="${1:-Box alert}"; BODY="${2:-}"
[ -z "$BODY" ] && [ ! -t 0 ] && BODY="$(cat)"
exec "$HOME/systems/lib/tg-notify.sh" "$TITLE" "$BODY" "${3:-default}"

# --- retired Discord path (unreachable) -------------------------------------
set -u
TITLE="${1:-Box alert}"
BODY="${2:-}"
[ -z "$BODY" ] && [ ! -t 0 ] && BODY="$(cat)"
PRIO="${3:-default}"
# Telegram migration parallel-run: mirror every alert to the 🔔 Ops Log topic.
# Fail-open; the Discord leg below is removed in Phase 4.
"$HOME/systems/lib/tg-notify.sh" "$TITLE" "$BODY" "$PRIO" || true
HOOK="$(sed -n 's/.*"ops-log": *"\([^"]*\)".*/\1/p' "$HOME/agentic-os/discord/config.json" 2>/dev/null)"
[ -n "$HOOK" ] || exit 0
case "$PRIO" in
  high|urgent) ICON="🔴" ;;
  min|low)     ICON="🟢" ;;
  *)           ICON="🔔" ;;
esac
# Discord blocks the Python-urllib user agent, so build JSON in python, send with curl.
PAYLOAD="$(python3 -c 'import json,sys; print(json.dumps({"username":"📦 Box","content":sys.argv[1].strip()[:1900]}))' "$ICON **$TITLE**
$BODY")"
curl -fsS -m 10 -X POST -H "Content-Type: application/json" -d "$PAYLOAD" "$HOOK" >/dev/null 2>&1 || true
