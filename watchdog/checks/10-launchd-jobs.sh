#!/bin/bash
# Check every registered systemd --user unit: active/loaded? last result ok? recently triggered?
# Migrated from launchd 2026-06-17 (box runs systemd --user, not launchd).
set -uo pipefail
WD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$WD_DIR/lib/common.sh"

while IFS='|' read -r unit max_age type; do
  case "$unit" in ''|\#*) continue;; esac
  name="cron:${unit%.service}"

  if ! systemctl --user cat "$unit" >/dev/null 2>&1; then
    fail "$name" "no systemd user unit '$unit'"
    continue
  fi

  if [ "$type" = "keepalive" ]; then
    state=$(systemctl --user show -p ActiveState --value "$unit" 2>/dev/null)
    if [ "$state" = "active" ]; then ok "$name" "running"; else fail "$name" "not active (state=$state)"; fi
    continue
  fi

  # timer-driven oneshot
  result=$(systemctl --user show -p Result --value "$unit" 2>/dev/null)
  if [ -n "$result" ] && [ "$result" != "success" ]; then
    fail "$name" "last run result=$result"
    continue
  fi
  tmr="${unit%.service}.timer"
  lt=$(systemctl --user show -p LastTriggerUSec --value "$tmr" 2>/dev/null)
  if [ -z "$lt" ] || [ "$lt" = "n/a" ]; then
    warn "$name" "scheduled but has not run yet"
    continue
  fi
  epoch=$(date -d "$lt" +%s 2>/dev/null || echo 0)
  age=$(age_hours "$epoch")
  if [ "$age" -gt "$max_age" ]; then
    fail "$name" "last run ${age}h ago (max ${max_age}h) — timer may be dead"
  else
    ok "$name" "healthy (last run ${age}h ago)"
  fi
done < "$WD_DIR/jobs.conf"
