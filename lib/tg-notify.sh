#!/usr/bin/env bash
# tg-notify.sh "Title" "body" [priority] — box alert to the fleet Telegram
# group's 🔔 Ops Log topic. Drop-in signature-compatible with discord-notify.sh
# (priority only picks the icon). Token + chat from ~/systems/tg-dev-bot/.env;
# topic cached in ~/systems/lib/.tg-ops-topic as <chat_id>:<topic_id> and
# auto-recreated if the group changes. Fail-open: never breaks the calling job.
set -u
TITLE="${1:-alert}"; BODY="${2:-}"; PRIO="${3:-default}"
ENV_FILE="$HOME/systems/tg-dev-bot/.env"
TOPIC_FILE="$HOME/systems/lib/.tg-ops-topic"
TOKEN=$(sed -n 's/^TELEGRAM_TOKEN=//p' "$ENV_FILE" 2>/dev/null)
CHAT=$(sed -n 's/^CHAT_ID=//p' "$ENV_FILE" 2>/dev/null)
[ -n "$TOKEN" ] && [ -n "$CHAT" ] || exit 0
CACHED=$(cat "$TOPIC_FILE" 2>/dev/null)
TOPIC=""
case "$CACHED" in "$CHAT:"*) TOPIC="${CACHED#*:}";; esac
if [ -z "$TOPIC" ]; then
  RES=$(curl -sS -m 15 "https://api.telegram.org/bot${TOKEN}/createForumTopic" \
    --data-urlencode "chat_id=${CHAT}" --data-urlencode "name=🔔 Ops Log" 2>/dev/null)
  TOPIC=$(printf '%s' "$RES" | python3 -c 'import json,sys
try: print(json.load(sys.stdin)["result"]["message_thread_id"])
except Exception: pass' 2>/dev/null)
  [ -n "$TOPIC" ] && printf '%s:%s\n' "$CHAT" "$TOPIC" > "$TOPIC_FILE"
fi
case "$PRIO" in
  high|urgent|max) ICON="🚨" ;;
  min|low)         ICON="ℹ️" ;;
  *)               ICON="📦" ;;
esac
TEXT="$ICON $TITLE"
[ -n "$BODY" ] && TEXT="$TEXT
$BODY"
# Telegram hard cap 4096; leave headroom.
TEXT=$(printf '%s' "$TEXT" | head -c 4000)
HTML=$(printf '%s' "$TEXT" | python3 "$HOME/systems/lib/tg_md.py" 2>/dev/null)
if [ -n "$HTML" ]; then
  OK=$(curl -sS -m 15 "https://api.telegram.org/bot${TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${CHAT}" \
    ${TOPIC:+--data-urlencode "message_thread_id=${TOPIC}"} \
    --data-urlencode "parse_mode=HTML" \
    --data-urlencode 'link_preview_options={"is_disabled":true}' \
    --data-urlencode "text=${HTML}" 2>/dev/null | head -c 12)
  case "$OK" in '{"ok":true'*) exit 0;; esac
fi
# fallback: plain text (bad HTML or converter unavailable)
curl -sS -m 15 "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${CHAT}" \
  ${TOPIC:+--data-urlencode "message_thread_id=${TOPIC}"} \
  --data-urlencode 'link_preview_options={"is_disabled":true}' \
  --data-urlencode "text=${TEXT}" >/dev/null 2>&1 || true
exit 0
