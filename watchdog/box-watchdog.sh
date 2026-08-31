#!/usr/bin/env bash
# box-watchdog — verify migrated systemd timers/services + core services; alert via Discord #ops-log.
# Replaces the Mac watchdog (launchd/CCC checks). Runs ~06:30, after the night crons.
set -uo pipefail
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
NOTIFY="$HOME/systems/lib/discord-notify.sh"
TIMERS="bq-clickup-perf verdict-miner winners-refresh comments-digest research-monitor ad-rank vtt-ingest vtt-digest research-deepdive sha-weekly-report creative-feedback-synth gbrain-weekly raw-ingest-scan agents-weekly agents-monthly box-doctor qa-smoke night-queue-resume self-improve-digest correction-capture skill-telemetry ccc-review"
WD_DIR="$HOME/systems/watchdog"; mkdir -p "$WD_DIR/reports"
fails=(); oks=()
for t in $TIMERS; do
  if ! systemctl --user is-active "$t.timer" >/dev/null 2>&1; then fails+=("$t.timer INACTIVE"); continue; fi
  if systemctl --user is-failed "$t.service" >/dev/null 2>&1; then fails+=("$t.service FAILED last run"); else oks+=("$t"); fi
done
systemctl --user is-active syncthing.service >/dev/null 2>&1 || fails+=("syncthing INACTIVE")
tailscale status >/dev/null 2>&1 || fails+=("tailscale DOWN")
for svc in camofox creative-command-center tablet-dash agentic-bots; do systemctl --user is-active "$svc.service" >/dev/null 2>&1 || fails+=("$svc.service INACTIVE"); done
[ -e "$HOME/.gbrain/brain.pglite" ] || fails+=("gbrain data missing")
TS="$(date "+%Y-%m-%d %H:%M")"
REPORT="$WD_DIR/reports/$(date +%Y-%m-%d).md"
{ echo "# Box Watchdog — $TS"; echo
  if [ ${#fails[@]} -eq 0 ]; then echo "**Status: OK** — ${#oks[@]} timers healthy, syncthing+tailscale up"
  else echo "**Status: FAIL** — ${#fails[@]} issue(s):"; printf -- "- 🔴 %s\n" "${fails[@]}"; fi
} > "$REPORT"
ln -sf "$REPORT" "$WD_DIR/reports/latest.md"
if [ ${#fails[@]} -eq 0 ]; then
  "$NOTIFY" "Box watchdog: all green" "${#oks[@]} timers OK, syncthing+tailscale up" min
else
  "$NOTIFY" "Box watchdog: ${#fails[@]} issue(s)" "$(printf "%s\n" "${fails[@]}")" high
fi
echo "watchdog status: ${#fails[@]} fails, ${#oks[@]} oks"
