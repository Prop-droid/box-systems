#!/usr/bin/env bash
# mic_audit.sh: the lit rule, checked without trusting the page (spec 14 section 0 item 12 and V7).
# Run by tablet-voice-micaudit.timer every 10 minutes, over adb only (never the Fully password):
#   - Fully's recording clients in Android's RecordActivityMonitor (only that section of dumpsys audio: the
#     event log after it names past sessions), the resumed activity and the display wakefulness, all read in
#     one adb call so they describe the same moment;
#   - once an hour the WebView and Fully versions (a change is the cue to re-run the V14 regression);
#   - by day, when the page should hold a socket, the box's own /health record of it.
# Prints one JSON line per run (journald): ts, top, act, awake, fully_recording, night, wv, fully_v, sock,
# nosock_run, verdict (ok, VIOLATION, night_rec, read_error or adb_down), transient.
#   VIOLATION  Fully recording while the resumed activity is not FullyActivity or the display is not awake
#              (screensaver, another app on top, screen off). A hit is read again CONFIRM_S (3) seconds later
#              and only a repeat counts, so a sample that lands inside the page's release cannot alarm.
#   night_rec  recording between 22:00 and 08:00: allowed after a touch on the page (V13 matches the samples
#              with touch entries in voice.log), so it is logged, never alerted.
# Alerts go to Discord #ops-log through lib/tg-notify.sh, once per key (keys in
# ~/systems/.state/tablet-voice-micaudit-last): violation:DAY; version:WEBVIEW/FULLY (the first run only
# records, in ~/systems/.state/tablet-voice-versions); nosock:DAY (three lit daytime runs in a row while
# flags.json has enabled and ws but /health shows no tablet socket: a dead 8766 forward, page or service);
# readerr:DAY (adb answers but the dumps do not parse, twice in a row). adb down: an adb_down line and no
# alert (tablet-disabled-watch and the night rearm already alert adb outages).
# Off-line test knobs (never in the unit): DRY_RUN=1 prints alerts instead of posting and writes no state;
# FAKE_TOP (fully, screensaver, other or none), FAKE_REC (a count), FAKE_AWAKE, FAKE_WV, FAKE_FV and
# FAKE_SOCK (true, false or down) override readings; ADB_BIN, NOTIFY, STATE_DIR, FLAGS_FILE, HEALTH_URL,
# NOW_HOUR and CONFIRM_S override programs, paths and timing (tests/test_mic_audit.sh uses a stub adb).
set -uo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

SERIAL="${TABLET_ADB:-192.168.1.89:5555}"
ADB_BIN="${ADB_BIN:-adb}"
NOTIFY="${NOTIFY:-$HOME/systems/lib/tg-notify.sh}"
STATE_DIR="${STATE_DIR:-$HOME/systems/.state}"
FLAGS_FILE="${FLAGS_FILE:-$HOME/tablet-assistant/static/voice/flags.json}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8766/health}"
CONFIRM_S="${CONFIRM_S:-3}"
REC_RE="${REC_RE:-de\.ozerov\.fully|uid:10312}"
DRY="${DRY_RUN:-0}"
LAST="$STATE_DIR/tablet-voice-micaudit-last"
VERS="$STATE_DIR/tablet-voice-versions"
NOSOCK="$STATE_DIR/tablet-voice-micaudit-nosock"
[ "$DRY" = 1 ] || mkdir -p "$STATE_DIR"

hour="${NOW_HOUR:-$(date +%H)}"
hour=$((10#$hour))
night=false
if [ "$hour" -ge 22 ] || [ "$hour" -lt 8 ]; then night=true; fi
today=$(date +%F)
now_hm=$(date +%H:%M)

# ------------------------------------------------------------------ helpers
put_state() {  # put_state FILE CONTENT: atomic write, skipped in DRY_RUN
  [ "$DRY" = 1 ] && return 0
  local tmp
  tmp=$(mktemp "$1.XXXXXX") || return 1
  printf '%s\n' "$2" > "$tmp" && mv -f "$tmp" "$1"
}

alert_once() {  # alert_once KEY TITLE BODY; returns 1 only when the post failed (the key is then not recorded)
  local sent=""
  grep -qxF "$1" "$LAST" 2>/dev/null && sent=1
  if [ "$DRY" = 1 ]; then
    printf 'DRY_RUN alert: %s: %s%s\n' "$2" "$3" "${sent:+ (already sent, a real run stays quiet)}"
    return 0
  fi
  [ -n "$sent" ] && return 0
  if "$NOTIFY" "$2" "$3" >/dev/null 2>&1; then
    put_state "$LAST" "$({ grep -vxF "$1" "$LAST" 2>/dev/null; printf '%s\n' "$1"; } | tail -n 100)"
    return 0
  fi
  echo "notify failed for $1, retried next run" >&2
  return 1
}

jstr() {  # a JSON string of a sanitised token, or null
  local v
  v=$(printf '%s' "$1" | tr -cd 'A-Za-z0-9._/:+-')
  if [ -z "$v" ]; then printf 'null'; else printf '"%s"' "$v"; fi
}

SNAP_CMD='dumpsys activity activities 2>/dev/null | grep -m1 "ResumedActivity:"; echo @@POWER; dumpsys power 2>/dev/null | grep -m1 "mWakefulness="; echo @@AUDIO; dumpsys audio 2>/dev/null | sed -n "/RecordActivityMonitor/,/Audio event log/p"; echo @@END'
VERS_CMD='dumpsys package com.google.android.webview 2>/dev/null | grep -m1 versionName=; echo @@; dumpsys package de.ozerov.fully 2>/dev/null | grep -m1 versionName='

snap() { timeout 20 "$ADB_BIN" -s "$SERIAL" shell "$SNAP_CMD" 2>/dev/null | tr -d '\r'; }

parse() {  # parse SNAPSHOT: sets top act awake rec (rec empty = the recorder section did not parse)
  local s="$1" topl aud
  topl=$(printf '%s\n' "$s" | awk '$0=="@@POWER"{exit} /ResumedActivity:/{print; exit}')
  act=$(printf '%s\n' "$topl" | grep -o -E '[A-Za-z0-9_.]+/[A-Za-z0-9_.$]+' | head -n 1)
  case "$act" in
    "") top=none ;;
    *ScreensaverActivity*) top=screensaver ;;
    de.ozerov.fully/*FullyActivity) top=fully ;;
    *) top=other ;;
  esac
  awake=$(printf '%s\n' "$s" | awk '$0=="@@AUDIO"{exit} f && /mWakefulness=/{sub(/.*mWakefulness=/, ""); print; exit} $0=="@@POWER"{f=1}' | tr -cd 'A-Za-z')
  aud=$(printf '%s\n' "$s" | awk '$0=="@@END"{exit} f{print} $0=="@@AUDIO"{f=1}')
  rec=""
  if printf '%s\n' "$s" | grep -qx '@@END' && printf '%s\n' "$aud" | grep -q 'RecordActivityMonitor'; then
    rec=$(printf '%s\n' "$aud" | grep -c -E "$REC_RE")
  fi
  [ -n "${FAKE_TOP:-}" ] && top="$FAKE_TOP" act=FAKE
  [ -n "${FAKE_AWAKE:-}" ] && awake="$FAKE_AWAKE"
  [ -n "${FAKE_REC:-}" ] && rec="$FAKE_REC"
  return 0
}

violation() { [ -n "$rec" ] && [ "$rec" -gt 0 ] && { [ "$top" != fully ] || [ "$awake" != Awake ]; }; }

line() {  # line VERDICT: the run's one JSON line
  local wv fv
  wv=$(sed -n 's/^webview=//p' "$VERS" 2>/dev/null)
  fv=$(sed -n 's/^fully=//p' "$VERS" 2>/dev/null)
  [ -n "${cur_wv:-}" ] && wv="$cur_wv"
  [ -n "${cur_fv:-}" ] && fv="$cur_fv"
  printf '{"ts": %s, "top": %s, "act": %s, "awake": %s, "fully_recording": %s, "night": %s, "wv": %s, "fully_v": %s, "sock": %s, "nosock_run": %s, "verdict": "%s", "transient": %s}\n' \
    "$(jstr "$(date -Iseconds)")" "$(jstr "${top:-}")" "$(jstr "${act:-}")" "$(jstr "${awake:-}")" "${rec:-null}" \
    "$night" "$(jstr "$wv")" "$(jstr "$fv")" "${sock_json:-null}" "${nos:-null}" "$1" "${transient:-false}"
}

# ------------------------------------------------------------------ readings
top="" act="" awake="" rec="" transient=false sock_json=null nos=null cur_wv="" cur_fv=""
timeout 15 "$ADB_BIN" connect "$SERIAL" >/dev/null 2>&1
s1=$(snap)
if ! printf '%s\n' "$s1" | grep -qx '@@END'; then
  if [ "$(timeout 20 "$ADB_BIN" -s "$SERIAL" shell echo ok 2>/dev/null | tr -d '\r')" != ok ]; then
    line adb_down
    exit 0
  fi
fi
parse "$s1"
if [ -z "$rec" ]; then                       # adb answered but the dump did not parse: read once more
  sleep "$CONFIRM_S"
  parse "$(snap)"
fi
if [ -z "$rec" ]; then
  line read_error
  alert_once "readerr:$today" "Tablet mic audit cannot read the recorder list" \
    "adb answers, but dumpsys audio has no RecordActivityMonitor section (twice in a row, $now_hm). Until this is fixed the audit is blind: check ~/systems/tablet-voice/mic_audit.sh against the device output (an Android or adb change)."
  exit 0
fi
if violation; then                           # confirm: one more read after CONFIRM_S
  sleep "$CONFIRM_S"
  p_top=$top p_awake=$awake p_rec=$rec p_act=$act
  s2=$(snap)
  parse "$s2"
  if [ -z "$rec" ]; then top=$p_top awake=$p_awake rec=$p_rec act=$p_act; fi   # unreadable: no sign of a release
  violation || transient=true
fi

# ------------------------------------------------------------------ versions, once an hour
if [ -n "${FAKE_WV:-}${FAKE_FV:-}" ] || [ ! -f "$VERS" ] || [ -n "$(find "$VERS" -mmin +55 2>/dev/null)" ]; then
  vt=$(timeout 20 "$ADB_BIN" -s "$SERIAL" shell "$VERS_CMD" 2>/dev/null | tr -d '\r')
  cur_wv=$(printf '%s\n' "$vt" | awk '$0=="@@"{exit} /versionName=/{sub(/.*versionName=/, ""); print; exit}' | tr -cd 'A-Za-z0-9._-')
  cur_fv=$(printf '%s\n' "$vt" | awk 'f && /versionName=/{sub(/.*versionName=/, ""); print; exit} $0=="@@"{f=1}' | tr -cd 'A-Za-z0-9._-')
  [ -n "${FAKE_WV:-}" ] && cur_wv="$FAKE_WV"
  [ -n "${FAKE_FV:-}" ] && cur_fv="$FAKE_FV"
  if [ -n "$cur_wv" ] && [ -n "$cur_fv" ]; then
    ok_rec=0
    if [ -f "$VERS" ]; then
      owv=$(sed -n 's/^webview=//p' "$VERS")
      ofv=$(sed -n 's/^fully=//p' "$VERS")
      if [ "$owv" != "$cur_wv" ] || [ "$ofv" != "$cur_fv" ]; then
        alert_once "version:$cur_wv/$cur_fv" "Tablet: WebView or Fully version changed" \
          "WebView $owv to $cur_wv, Fully $ofv to $cur_fv ($now_hm). Re-run the V14 regression (V7 release check, V9 churn blocks a to d, V11 mute proof) before trusting the lit rule again." || ok_rec=1
      fi
    elif [ "$DRY" = 1 ]; then
      echo "DRY_RUN note: no recorded versions yet; a real run records WebView $cur_wv and Fully $cur_fv"
    fi
    [ "$ok_rec" = 0 ] && put_state "$VERS" "$(printf 'webview=%s\nfully=%s' "$cur_wv" "$cur_fv")"
  fi
fi

# ------------------------------------------------------------------ the tablet socket, by day while lit
flags_ws_on() {
  python3 -I -c 'import json, sys
f = json.load(open(sys.argv[1]))
sys.exit(0 if f.get("enabled") is True and f.get("ws") is True else 1)' "$FLAGS_FILE" 2>/dev/null
}
health_sock() {
  curl -s -m 3 "$HEALTH_URL" 2>/dev/null | python3 -I -c 'import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print("down")
else:
    print("true" if d.get("tablet_connected") is True else "false")' 2>/dev/null
}
if [ "$night" = false ] && [ "$top" = fully ] && [ "$awake" = Awake ] && flags_ws_on; then
  sock="${FAKE_SOCK:-$(health_sock)}"
  [ -n "$sock" ] || sock=down
  case "$sock" in true|false) sock_json=$sock ;; *) sock_json='"down"' ;; esac
  prev=$(tr -cd '0-9' < "$NOSOCK" 2>/dev/null)
  if [ "$sock" = true ]; then nos=0; else nos=$(( ${prev:-0} + 1 )); fi
  if [ "$nos" -ge 3 ]; then
    alert_once "nosock:$today" "Tablet voice: no socket while lit" \
      "Three lit daytime runs in a row ($now_hm) with flags.json enabled and ws, but the box has no tablet socket (/health: $sock). Check the 8766 forward on the tablet (dash-proxy.sh), the page (initError) and tablet-voice.service."
  fi
else
  nos=0
fi
put_state "$NOSOCK" "$nos"

# ------------------------------------------------------------------ verdict
if violation; then
  line VIOLATION
  alert_once "violation:$today" "Tablet: microphone open while dark" \
    "Android shows Fully recording ($rec client) while the resumed activity is $top ($act) and the display is $awake ($now_hm). The page's own ledger cannot show this. Check voice.log, then re-run the V7 release check; kill switch: vflags enabled=false and reload_dash."
elif [ -n "$rec" ] && [ "$rec" -gt 0 ] && [ "$night" = true ]; then
  line night_rec
else
  line ok
fi
exit 0
