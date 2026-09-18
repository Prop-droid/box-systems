#!/usr/bin/env bash
# DISCORD-RESTORED (Tomas 2026-09-18): feed posts go back to Discord channels
# via discord-post.sh, posting AS the fleet bot that owned the Telegram topic,
# so replies land where that channel agent reads. Callers unchanged:
#   tg-post.sh <topic-name> <tg-instance> [file]    (stdin if no file)
# The topic name is dropped — the Discord channel itself is the feed.
# Telegram original: git log (retired 2026-09-18).
set -u
TOPIC="${1:?topic name}"; INSTANCE="${2:?instance}"; FILE="${3:-}"
case "$INSTANCE" in
  tg-creative-bot) CH=1531648564932120737; VAR=CREATIVE_TOKEN ;;  # #creative
  tg-ea-bot)       CH=1531571387108429964; VAR=EA_TOKEN ;;        # #assistant
  tg-coach-bot)    CH=1531564790068285543; VAR=QA_TOKEN ;;        # #coach (Štuikys token)
  tg-qa-bot)       CH=1531922639457620111; VAR=COPY_TOKEN ;;      # #qa
  *)               CH=1531564369672929290; VAR=DEV_TOKEN ;;       # #dev
esac
exec "$HOME/systems/lib/discord-post.sh" "$CH" "$VAR" ${FILE:+"$FILE"}
