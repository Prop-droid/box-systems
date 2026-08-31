#!/usr/bin/env bash
# Dashboard tablet day/night mode + self-heal via Fully Kiosk REST.
#   night: motion detection ON (low sensitivity), black screensaver, motion wakes
#   day:   motion detection ON (high sensitivity), screen blanks after idle, motion wakes
#   relaunch: 09:00 daily — relaunch Fully if it was exited (movie night);
#          needs Wireless debugging ON on the tablet for the adb path
#   rearm: every-15-min self-heal —
#          Fully dead   -> relaunch over adb if the tablet is idle (never steals
#                          foreground while Tomas is using another app);
#                          if adb can't reach it, Discord-alert once per outage
#          Fully alive  -> re-assert the current mode's settings if they drifted
#                          (a mode run that fired while Fully was dead is lost
#                          otherwise — that's the 2026-08-12 "motion gone" bug);
#                          at night restart the screensaver if knocked out
set -u
PW="tomastab2026"
PKG="de.ozerov.fully"
STATE_DIR="$HOME/systems/.state"
mkdir -p "$STATE_DIR"
DEAD_FLAG="$STATE_DIR/tablet-fully-dead"
IP_CACHE="$STATE_DIR/tablet-ip"
NOTIFY="$HOME/systems/lib/tg-notify.sh"

# Tablet DHCP IP drifts (router subnet changed 2026-08-28: 192.168.0.x → .1.x).
# Probe Fully REST directly — the old adb-derived IP broke exactly when adb was
# disconnected (silent-fail mode).
CANDIDATES="192.168.1.89 192.168.0.160 192.168.0.161"
discover_ip() {
  IP=""
  local cand
  for cand in $(cat "$IP_CACHE" 2>/dev/null) $CANDIDATES; do
    if curl -s -m 4 "http://$cand:2323/?password=$PW&cmd=deviceInfo&type=json" | grep -q '"deviceName"'; then
      IP="$cand"
      echo "$cand" > "$IP_CACHE"
      return 0
    fi
  done
  return 1
}
discover_ip || true

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
setting() { # setting <key> -> value from cached listSettings dump
  python3 -c "import json,sys; print(json.load(open('$STATE_DIR/tablet-settings.json')).get('$1',''))" 2>/dev/null
}
fetch_settings() {
  curl -s -m 10 "http://$IP:2323/?password=$PW&cmd=listSettings&type=json" > "$STATE_DIR/tablet-settings.json" 2>/dev/null
}

adb_serial() { # tablet only — never match the Pixel, which is also LAN adb
  adb devices 2>/dev/null | awk '$2=="device" && ($1 ~ /192\.168\.1\.89/ || $1 ~ /192\.168\.0\.160/ || $1 ~ /192\.168\.0\.161/) {print $1; exit}'
}
tablet_idle() { # safe to steal foreground: screen off/dozing, or Fully/launcher focused
  local s="$1" awake focus
  awake=$(adb -s "$s" shell dumpsys power 2>/dev/null | grep -m1 "mWakefulness=")
  case "$awake" in *Awake*) ;; *) return 0 ;; esac
  focus=$(adb -s "$s" shell dumpsys window 2>/dev/null | grep -m1 "mCurrentFocus")
  case "$focus" in
    *"$PKG"*|*[Ll]auncher*) return 0 ;;
    *) return 1 ;;
  esac
}
relaunch_fully() { # rc 0 = relaunched, 1 = no adb path, 2 = tablet in use
  local s
  s=$(adb_serial)
  if [ -z "$s" ]; then
    bash "$HOME/agent-box-setup/tablet-control/adb-tablet-connect.sh" >/dev/null 2>&1 || true
    s=$(adb_serial)
  fi
  [ -z "$s" ] && return 1
  tablet_idle "$s" || return 2
  adb -s "$s" shell am force-stop "$PKG" >/dev/null 2>&1
  adb -s "$s" shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
  sleep 10
  return 0
}

# Sensitivity: 90 by day (75 proved deaf, verified live 2026-08-06); 50 by night
# (90 was so hot camera noise in the dark counted as motion — bright-all-night
# bug 2026-07-28).
mode_for_hour() {
  local h; h=$(date +%H)
  if [ "$h" -ge 22 ] || [ "$h" -lt 8 ]; then echo night; else echo day; fi
}
# 23:00–08:00 Tomas isn't using the tablet — down alerts are noise (2026-08-26).
# A future epoch in SNOOZE_FILE mutes ALL tablet alerts until then ("ignore tablet
# for a week", 2026-08-28). Delete the file to unmute early.
SNOOZE_FILE="$STATE_DIR/tablet-alerts-snooze-until"
quiet_hours() {
  local h until
  until=$(cat "$SNOOZE_FILE" 2>/dev/null)
  [ -n "$until" ] && [ "$(date +%s)" -lt "$until" ] 2>/dev/null && return 0
  h=$(date +%H); [ "$h" -ge 23 ] || [ "$h" -lt 8 ]
}
apply_settings() { # apply_settings day|night — settings only, no screen commands
  local sens=90
  [ "$1" = night ] && sens=50
  f "cmd=setBooleanSetting&key=motionDetection&value=true"
  f "cmd=setBooleanSetting&key=screenOnOnMotion&value=true"
  f "cmd=setBooleanSetting&key=stopScreensaverOnMotion&value=true"
  f "cmd=setStringSetting&key=motionSensitivity&value=$sens"
  f "cmd=setStringSetting&key=timeToScreensaverV2&value=180"
}

ensure_alive() { # rc 0 = Fully reachable (possibly after relaunch)
  if [ -n "$IP" ]; then
    if [ -f "$DEAD_FLAG" ]; then
      rm -f "$DEAD_FLAG"
      # A mode run may have fired into the void while Fully was dead — resync.
      apply_settings "$(mode_for_hour)"
      echo "fully recovered, $(mode_for_hour) settings re-applied"
    fi
    return 0
  fi
  relaunch_fully
  case $? in
    0)
      if discover_ip; then
        rm -f "$DEAD_FLAG"
        apply_settings "$(mode_for_hour)"
        echo "fully was dead — relaunched via adb, $(mode_for_hour) settings applied"
        return 0
      fi
      ;;
    2)
      echo "fully down but tablet in use — leaving it alone" >&2
      return 1
      ;;
  esac
  # Alert once per outage; quiet hours write "suppressed" into the flag so an
  # outage persisting past 08:00 still posts on the next rearm.
  FLAG_STATE="$(cat "$DEAD_FLAG" 2>/dev/null)"
  if [ ! -f "$DEAD_FLAG" ] || { [ "$FLAG_STATE" = suppressed ] && ! quiet_hours; }; then
    if quiet_hours; then
      echo suppressed > "$DEAD_FLAG"
      echo "fully down — alert suppressed (quiet hours)" >&2
    else
      echo notified > "$DEAD_FLAG"
      [ -x "$NOTIFY" ] && "$NOTIFY" "Tablet dashboard down" \
        "Fully Kiosk is not running and adb can't relaunch it (Wireless debugging off?). Motion detection is OFF until Fully is reopened on the tablet." \
        high || true
    fi
  fi
  echo "fully unreachable and no adb relaunch path" >&2
  return 1
}

case "${1:-}" in
  night)
    # Fully down is tolerated here (Tomas exits it to watch movies) — the
    # 09:00 relaunch unit / rearm restore it; only they treat down as notable.
    ensure_alive || { echo "fully down — tolerated, relaunch/rearm will restore"; exit 0; }
    apply_settings night
    f "cmd=startScreensaver"
    ;;
  day)
    ensure_alive || { echo "fully down — tolerated, relaunch/rearm will restore"; exit 0; }
    apply_settings day
    f "cmd=stopScreensaver"
    f "cmd=screenOn"
    ;;
  relaunch)
    # 09:00 daily: bring Fully back after an evening of movie-watching.
    # ensure_alive does the whole job (adb relaunch, settings resync, alert
    # once per outage if adb is unreachable); in-use/no-adb is not a unit
    # failure — rearm keeps retrying every 15 min.
    ensure_alive || exit 0
    ;;
  rearm)
    ensure_alive || exit 0
    # Drift check: a mode run that failed leaves stale settings (e.g. night
    # sensitivity 50 all day). Re-assert quietly when they don't match the hour.
    MODE=$(mode_for_hour)
    WANT=90; [ "$MODE" = night ] && WANT=50
    fetch_settings
    if [ "$(setting motionDetection)" != "True" ] || [ "$(setting motionSensitivity)" != "$WANT" ]; then
      echo "settings drifted (motionDetection=$(setting motionDetection) sensitivity=$(setting motionSensitivity), want $MODE/$WANT) — re-applying"
      apply_settings "$MODE"
    fi
    if [ "$MODE" = night ] || [ "${FORCE:-0}" = 1 ]; then
      in_screensaver || f "cmd=startScreensaver"
    fi
    ;;
  *) echo "usage: $0 night|day|rearm" >&2; exit 2 ;;
esac
