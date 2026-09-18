#!/usr/bin/env bash
# Post a box alert to Discord #ops-log (Agentic OS server).
# Usage: discord-notify.sh "Title" ["body"] [priority]   (body may come from stdin)
# Priority maps to an icon only: high/urgent=red, min/low=green, else bell.
# Replaces the old ntfy tablet topic (tomas-tab-958e4431) per Tomas 2026-08-05.
set -u
TITLE="${1:-Box alert}"
BODY="${2:-}"
[ -z "$BODY" ] && [ ! -t 0 ] && BODY="$(cat)"
PRIO="${3:-default}"
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
