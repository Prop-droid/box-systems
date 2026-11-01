#!/usr/bin/env bash
# tablet-disabled-watch: daily 09:30 check that every debloated tablet app is still disabled.
# Why: a Play Store update re-enabled a disabled app one minute after the disable
# (Files by Google, 2026-10-31 20:32). Alert only, never re-disables by itself.
#   expected list: ~/systems/tablet-disabled-expected.txt (one package per line)
#   alerts:        Discord #ops-log via lib/tg-notify.sh, once per distinct problem
#   adb down:      one alert per outage (after a tablet reboot someone must tap
#                  "Always allow" + Allow on the Wireless debugging prompt)
#   dry run:       DRY_RUN=1 bash ~/systems/tablet-disabled-watch.sh
#                  (EXPECTED_FILE=/path/to/list simulates a problem)
set -uo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
SERIAL="${TABLET_ADB:-192.168.1.89:5555}"
EXPECTED_FILE="${EXPECTED_FILE:-$HOME/systems/tablet-disabled-expected.txt}"
STATE_DIR="$HOME/systems/.state"
LAST="$STATE_DIR/tablet-disabled-watch-last"   # key of the last alert; empty = all good
NOTIFY="$HOME/systems/lib/tg-notify.sh"
mkdir -p "$STATE_DIR"

alert_once() { # alert_once KEY TITLE BODY
  if [ "$(cat "$LAST" 2>/dev/null)" = "$1" ]; then echo "already alerted ($1)"; return 0; fi
  if [ "${DRY_RUN:-0}" = 1 ]; then printf 'DRY_RUN alert: %s\n%s\n' "$2" "$3"; return 0; fi
  "$NOTIFY" "$2" "$3"
  printf '%s' "$1" > "$LAST"
}
pkgs() { # pkgs FLAG: sorted package names from "pm list packages FLAG"
  timeout 30 adb -s "$SERIAL" shell pm list packages "$1" | tr -d '\r' | sed -n 's/^package://p' | sort -u
}

[ -r "$EXPECTED_FILE" ] || { echo "expected list missing: $EXPECTED_FILE" >&2; exit 1; }
timeout 15 adb connect "$SERIAL" >/dev/null 2>&1
if [ "$(timeout 20 adb -s "$SERIAL" shell echo ok 2>/dev/null | tr -d '\r')" != ok ]; then
  echo "adb unreachable ($SERIAL), check skipped"
  alert_once adb-down "Tablet adb unreachable" "The daily debloat check could not reach $SERIAL. After a tablet reboot, tap \"Always allow on this network\" + Allow on the Wireless debugging prompt."
  exit 0
fi

expected=$(grep -v -E '^[[:space:]]*(#|$)' "$EXPECTED_FILE" | awk '{print $1}' | sort -u)
disabled=$(pkgs -d) || { echo "pm list packages -d failed" >&2; exit 1; }
enabled=$(pkgs -e) || { echo "pm list packages -e failed" >&2; exit 1; }
if [ -z "$disabled" ] || [ -z "$enabled" ]; then
  echo "empty package list from pm (adb glitch?), not judging" >&2; exit 1
fi

n_exp=$(printf '%s\n' "$expected" | grep -c .)
missing=$(comm -23 <(printf '%s\n' "$expected") <(printf '%s\n' "$disabled") | grep .)
if [ -z "$missing" ]; then
  echo "ok: all $n_exp expected packages disabled ($(printf '%s\n' "$disabled" | grep -c .) disabled in total)"
  [ "${DRY_RUN:-0}" = 1 ] || : > "$LAST"
  exit 0
fi

back=$(comm -12 <(printf '%s\n' "$missing") <(printf '%s\n' "$enabled") | grep .)
gone=$(comm -23 <(printf '%s\n' "$missing") <(printf '%s\n' "$enabled") | grep .)
n_miss=$(printf '%s\n' "$missing" | grep -c .)
body=""
[ -n "$back" ] && body+="Enabled again (usually a Play Store update):"$'\n'"$(printf '%s\n' "$back" | sed 's/^/  /')"$'\n'
[ -n "$gone" ] && body+="No longer installed for user 0:"$'\n'"$(printf '%s\n' "$gone" | sed 's/^/  /')"$'\n'
body+="Re-disable: adb -s $SERIAL shell pm disable-user --user 0 <package>"$'\n'
body+="Wanted it back? Remove it from ~/systems/tablet-disabled-expected.txt"
echo "PROBLEM: $n_miss of $n_exp expected packages are not disabled:"
printf '%s\n' "$missing"
alert_once "missing:$(printf '%s,' $missing)" "Tablet: $n_miss debloated app(s) came back" "$body"
exit 0
