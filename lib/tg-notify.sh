#!/usr/bin/env bash
# tg-notify.sh "Title" "body" [priority] — box alert to the Agent OS Telegram
# group's Ops Log topic. Drop-in signature-compatible with discord-notify.sh
# (priority only picks the icon). Token + chat from ~/systems/tg-dev-bot/.env;
# topic id cached in ~/systems/lib/.tg-ops-topic (created once via
# createForumTopic). Fail-open: never breaks the calling job.
set -u
TITLE="${1:-alert}"; BODY="${2:-}"; PRIO="${3:-default}"
ENV_FILE="$HOME/systems/tg-dev-bot/.env"
TOPIC_FILE="$HOME/systems/lib/.tg-ops-topic"
TOKEN=$(sed -n 's/^TELEGRAM_TOKEN=//p' "$ENV_FILE" 2>/dev/null)
CHAT=$(sed -n 's/^CHAT_ID=//p' "$ENV_FILE" 2>/dev/null)
TOPIC=$(cat "$TOPIC_FILE" 2>/dev/null)
[ -n "$TOKEN" ] && [ -n "$CHAT" ] || exit 0
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
curl -sS -m 15 "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${CHAT}" \
  ${TOPIC:+--data-urlencode "message_thread_id=${TOPIC}"} \
  --data-urlencode "text=${TEXT}" >/dev/null 2>&1 || true
exit 0
