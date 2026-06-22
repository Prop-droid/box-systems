#!/usr/bin/env bash
# Put the dashboard tablet's screen to sleep / wake it, over adb.
# Reduces OLED heat + battery wear + burn-in during dead hours.
# Usage: tablet-screen.sh off|on
set -u
ADB="${ADB:-/usr/bin/adb}"
TABLET_IP="${TABLET_IP:-192.168.0.160}"
DEV="${TABLET_IP}:5555"

# Make sure we're connected (the watchdog usually keeps this up, but be safe).
"$ADB" connect "$DEV" >/dev/null 2>&1

case "${1:-}" in
  off)
    # KEYCODE_SLEEP=223 forces the screen off (won't toggle-on like POWER).
    "$ADB" -s "$DEV" shell input keyevent 223
    ;;
  on)
    # KEYCODE_WAKEUP=224 forces the screen on (no-op if already on).
    "$ADB" -s "$DEV" shell input keyevent 224
    ;;
  *)
    echo "usage: $0 off|on" >&2; exit 2;;
esac
