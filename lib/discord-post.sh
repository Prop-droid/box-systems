#!/usr/bin/env bash
# TELEGRAM-ONLY RULE (Tomas 2026-08-31): agent-facing feed posts go to fleet
# Telegram topics via tg-post.sh. This shim keeps every existing caller working
# unchanged: the Discord (channel_id, TOKEN_VAR) pair maps to a (topic,
# tg-instance) pair — replies in the topic route to the same agent that owned
# the Discord channel. Original Discord body: git log (retired 2026-08-31).
# Usage (unchanged): discord-post.sh <channel_id> <TOKEN_VAR> [file]
set -u
CH="${1:?channel id}"; VAR="${2:?token var}"; FILE="${3:-}"
case "$VAR" in
  CREATIVE_TOKEN) TOPIC="📊 Creative Feed";   INST="tg-creative-bot" ;;
  EA_TOKEN)       TOPIC="📋 Launch Details";  INST="tg-ea-bot" ;;
  QA_TOKEN)       TOPIC="🧪 QA Feed";         INST="tg-qa-bot" ;;
  COACH_TOKEN)    TOPIC="🏃 Coach Feed";      INST="tg-coach-bot" ;;
  *)              TOPIC="🛠 Dev Feed";        INST="tg-dev-bot" ;;
esac
exec "$HOME/systems/lib/tg-post.sh" "$TOPIC" "$INST" ${FILE:+"$FILE"}
