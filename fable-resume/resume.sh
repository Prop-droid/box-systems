#!/usr/bin/env bash
# fable-resume: relaunch the fable-window driver if tasks are pending and no driver runs.
# Driver launches as a DETACHED transient systemd unit (a tmux/child launched directly from
# a oneshot service dies with the service cgroup - learned 2026-07-05).
B="$HOME/fable-window"
[ -f "$B/STOP" ] && exit 0
[ -f "$HOME/.claude/PAUSE_CLAUDE_BG" ] && exit 0
grep -l "LIMIT-GAVE-UP" "$B"/logs/*.done 2>/dev/null | while read -r f; do rm -f "$f"; done
pending=0
for t in "$B"/tasks/*.task; do
  [ -f "$B/logs/$(basename "$t" .task).done" ] || { pending=1; break; }
done
[ "$pending" -eq 0 ] && exit 0
pgrep -f "^bash .*fable-window/driver.sh" >/dev/null && exit 0
systemctl --user is-active --quiet fable-driver && exit 0
systemd-run --user --unit fable-driver --collect \
  bash -c "bash $B/driver.sh >> $B/logs/driver.console 2>&1"
curl -s -d "fable-resume: driver relaunched $(date +%H:%M)" https://ntfy.sh/tomas-tab-958e4431 >/dev/null
