#!/bin/bash
# EA daily calendar digest (today + tomorrow) -> EA Telegram group. systemd: ea-calendar.timer
set -uo pipefail
exec /home/tomas/tablet-assistant/venv/bin/python /home/tomas/systems/ea-calendar/digest.py \
  >> /home/tomas/systems/ea-calendar/logs/run.log 2>&1
