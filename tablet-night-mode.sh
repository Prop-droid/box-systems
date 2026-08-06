#!/usr/bin/env bash
# Dashboard tablet day/night mode via Fully Kiosk REST.
#   night: motion detection ON (low sensitivity), black screensaver, motion wakes
#   day:   screen always on, motion detection OFF (camera is on-demand only)
#   rearm: overnight backstop - if screensaver got knocked out by motion/noise,
#          restart it; no-op outside 22:00-08:00 unless FORCE=1
set -u
PW="tomastab2026"
IP="$(adb devices 2>/dev/null | grep -oE "192\.168\.[0-9]+\.[0-9]+" | head -1)"
IP="${IP:-192.168.0.161}"
f() {
  out=$(curl -s -m 10 "http://$IP:2323/?password=$PW&$1&type=json")
  case "$out" in
    *"\"status\":\"OK\""*) ;;
    *) echo "fully FAIL $1 -> $out" >&2 ;;
  esac
}
in_screensaver() {
  curl -s -m 10 "http://$IP:2323/?password=$PW&cmd=deviceInfo&type=json" | grep -q "\"isInScreensaver\":true"
}

case "${1:-}" in
  night)
    f "cmd=setBooleanSetting&key=motionDetection&value=true"
    f "cmd=setBooleanSetting&key=screenOnOnMotion&value=true"
    f "cmd=setBooleanSetting&key=stopScreensaverOnMotion&value=true"
    # 90 was so hot that camera noise in the dark counted as motion and the
    # screensaver never got a 180s idle window (bright-all-night bug, 2026-07-28)
    f "cmd=setStringSetting&key=motionSensitivity&value=50"
    f "cmd=setStringSetting&key=timeToScreensaverV2&value=180"
    f "cmd=startScreensaver"
    ;;
  day)
    # Motion-wake by day too (restored 2026-08-05 per Tomas): screen blanks
    # after 180s idle, wakes when someone's in front of the camera.
    f "cmd=setBooleanSetting&key=motionDetection&value=true"
    f "cmd=setBooleanSetting&key=screenOnOnMotion&value=true"
    f "cmd=setBooleanSetting&key=stopScreensaverOnMotion&value=true"
    # 90 by day: 75 proved deaf again by 2026-08-06 (verified live: screensaver
    # ignored a person moving in frame at 75, woke in ~25s at 90). Night keeps 50.
    f "cmd=setStringSetting&key=motionSensitivity&value=90"
    f "cmd=setStringSetting&key=timeToScreensaverV2&value=180"
    f "cmd=stopScreensaver"
    f "cmd=screenOn"
    ;;
  rearm)
    H=$(date +%H)
    if [ "$H" -ge 22 ] || [ "$H" -lt 8 ] || [ "${FORCE:-0}" = 1 ]; then
      in_screensaver || f "cmd=startScreensaver"
    fi
    ;;
  *) echo "usage: $0 night|day|rearm" >&2; exit 2 ;;
esac
