#!/usr/bin/env bash
# Restart each channel bot at a moment when it runs no claude turn, so no reply is cut.
# A bot keeps its old code and .env until it restarts (dev_bot.py loads both once at start).
# Usage: restart_when_idle.sh [max_wait_seconds]      default 7200
# Run it detached, never from inside a bot turn's own process tree:
#   systemd-run --user --unit bots-restart-when-idle --collect bash ~/systems/dev-bot/restart_when_idle.sh
set -u
UNITS=(${BOT_UNITS:-dev-bot creative-bot ea-bot coach-bot general-bot})
deadline=$(( $(date +%s) + ${1:-7200} ))
busy() {  # true when the unit's cgroup holds a claude process
  local cg pid
  cg=$(systemctl --user show -p ControlGroup --value "$1.service")
  [ -n "$cg" ] && [ -r "/sys/fs/cgroup$cg/cgroup.procs" ] || return 1
  while read -r pid; do
    [ "$(cat "/proc/$pid/comm" 2>/dev/null)" = "claude" ] && return 0
  done < "/sys/fs/cgroup$cg/cgroup.procs"
  return 1
}
pending=("${UNITS[@]}")
while [ ${#pending[@]} -gt 0 ] && [ "$(date +%s)" -lt "$deadline" ]; do
  next=()
  for u in "${pending[@]}"; do
    if busy "$u"; then next+=("$u"); continue; fi
    sleep 20; if busy "$u"; then next+=("$u"); continue; fi   # idle twice, 20 s apart
    systemctl --user restart "$u.service" && echo "$(date '+%F %T') restarted $u" || echo "$(date '+%F %T') FAILED to restart $u"
  done
  pending=("${next[@]+"${next[@]}"}")
  [ ${#pending[@]} -gt 0 ] && sleep 30
done
[ ${#pending[@]} -eq 0 ] && echo "$(date '+%F %T') all bots restarted" || echo "$(date '+%F %T') gave up, still busy: ${pending[*]}"
