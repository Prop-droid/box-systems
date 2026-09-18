#!/usr/bin/env bash
# DISCORD-RESTORED (Tomas 2026-09-18): "lets migrate back from telegram to
# discord". This is now a shim to discord-notify.sh (#ops-log webhook) so every
# tg-notify caller keeps working unchanged. Telegram original: git log
# (retired 2026-09-18; restore from history to flip back).
TITLE="${1:-alert}"; BODY="${2:-}"
[ -z "$BODY" ] && [ ! -t 0 ] && BODY="$(cat)"
exec "$HOME/systems/lib/discord-notify.sh" "$TITLE" "$BODY" "${3:-default}"
