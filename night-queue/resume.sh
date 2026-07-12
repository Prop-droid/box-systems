#!/usr/bin/env bash
# night-queue resume: relaunch queue.sh if tasks are pending and no driver runs.
# Driver launches as a DETACHED transient systemd unit (a child launched directly
# from a oneshot service dies with the service cgroup - learned 2026-07-05).
NQ_HOME="$HOME/systems/night-queue"
Q="${NQ_DIR:-$NQ_HOME/queue}"
[ -f "$Q/STOP" ] && exit 0
[ -f "$HOME/.claude/PAUSE_CLAUDE_BG" ] && exit 0
[ -f "$Q/PAUSE" ] && exit 0
# LIMIT-GAVE-UP markers get another chance on the next resume tick
grep -l "LIMIT-GAVE-UP" "$Q"/logs/*.done 2>/dev/null | while read -r f; do rm -f "$f"; done
pending=0
for t in "$Q"/tasks/*.task; do
  [ -f "$t" ] || continue
  [ -f "$Q/logs/$(basename "$t" .task).done" ] || { pending=1; break; }
done
[ "$pending" -eq 0 ] && exit 0
pgrep -f "^bash $NQ_HOME/queue.sh" >/dev/null && exit 0
systemctl --user is-active --quiet night-queue-driver && exit 0
systemd-run --user --unit night-queue-driver --collect \
  bash -c "NQ_DIR='$Q' bash $NQ_HOME/queue.sh >> $Q/logs/driver.console 2>&1"
curl -sm 10 -d "night-queue: driver relaunched $(date +%H:%M)" \
  "https://ntfy.sh/${NQ_NTFY:-tomas-tab-958e4431}" >/dev/null || true
