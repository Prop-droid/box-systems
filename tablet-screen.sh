#!/usr/bin/env bash
# Put the dashboard tablet's screen to sleep / wake it, over adb.
# Reduces OLED heat + battery wear + burn-in during dead hours.
# Usage: tablet-screen.sh off|on
set -u
ADB="${ADB:-/usr/bin/adb}"
TABLET_IP="${TABLET_IP:-192.168.0.160}"
CONNECT="${CONNECT:-/home/tomas/agent-box-setup/tablet-control/adb-tablet-connect.sh}"

# Ensure we're connected (reboot-proof mDNS discovery lives in the watchdog script).
ADB="$ADB" TABLET_IP="$TABLET_IP" "$CONNECT" >/dev/null 2>&1 || true

# Find the tablet's currently-connected serial (port rotates across reboots).
DEV="$("$ADB" devices 2>/dev/null | awk -v ip="$TABLET_IP" '$2=="device" && index($1,ip){print $1; exit}')"
[ -z "$DEV" ] && { echo "tablet not connected" >&2; exit 1; }

case "${1:-}" in
  off) "$ADB" -s "$DEV" shell input keyevent 223 ;;  # KEYCODE_SLEEP
  on)  "$ADB" -s "$DEV" shell input keyevent 224 ;;  # KEYCODE_WAKEUP
  *)   echo "usage: $0 off|on" >&2; exit 2 ;;
esac
