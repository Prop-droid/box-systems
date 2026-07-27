#!/usr/bin/env bash
# Dashboard tablet day/night mode via Fully Kiosk REST.
#   night: motion detection ON, black screensaver after 180s no motion, motion wakes
#   day:   screen always on, motion detection OFF (camera is on-demand only)
# Usage: tablet-night-mode.sh night|day
set -u
PW="tomastab2026"
IP="$(adb devices 2>/dev/null | grep -oE '192\.168\.[0-9]+\.[0-9]+' | head -1)"
IP="${IP:-192.168.0.161}"
f() { curl -s -m 10 "http://$IP:2323/?password=$PW&$1" >/dev/null; }

case "${1:-}" in
  night)
    f "cmd=setBooleanSetting&key=motionDetection&value=true"
    f "cmd=setBooleanSetting&key=screenOnOnMotion&value=true"
    f "cmd=setBooleanSetting&key=stopScreensaverOnMotion&value=true"
    f "cmd=setStringSetting&key=timeToScreensaverV2&value=180"
    f "cmd=startScreensaver"
    ;;
  day)
    f "cmd=setStringSetting&key=timeToScreensaverV2&value=0"
    f "cmd=setBooleanSetting&key=motionDetection&value=false"
    f "cmd=stopScreensaver"
    f "cmd=screenOn"
    ;;
  *) echo "usage: $0 night|day" >&2; exit 2 ;;
esac
