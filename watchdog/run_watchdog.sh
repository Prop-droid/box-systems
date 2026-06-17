#!/bin/bash
# System watchdog: runs all check modules, writes a report, notifies on failures.
# Daily via com.tomas.watchdog (08:30). Weekly checks (checks/weekly-*.sh) run Mondays
# or when invoked with --weekly.
set -uo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$PATH"
WD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORT_DIR="$WD_DIR/reports"
mkdir -p "$REPORT_DIR"

TS="$(date +%Y-%m-%d_%H%M)"
export RESULTS_FILE="$(mktemp /tmp/watchdog-results.XXXXXX)"
trap 'rm -f "$RESULTS_FILE"' EXIT

RUN_WEEKLY=0
[ "$(date +%u)" = "1" ] && RUN_WEEKLY=1
[ "${1:-}" = "--weekly" ] && RUN_WEEKLY=1

for chk in "$WD_DIR"/checks/*.sh; do
  base=$(basename "$chk")
  case "$base" in
    weekly-*) [ "$RUN_WEEKLY" = "1" ] || continue ;;
  esac
  # 300s cap per check; a hung check must not kill the run
  if command -v gtimeout >/dev/null; then gtimeout 300 bash "$chk" || echo "FAIL|runner:$base|check crashed or timed out" >>"$RESULTS_FILE"
  else bash "$chk" || echo "FAIL|runner:$base|check crashed" >>"$RESULTS_FILE"; fi
done

FAILS=$(grep -c '^FAIL|' "$RESULTS_FILE" || true)
WARNS=$(grep -c '^WARN|' "$RESULTS_FILE" || true)
OKS=$(grep -c '^OK|'   "$RESULTS_FILE" || true)
STATUS=OK; [ "$WARNS" -gt 0 ] && STATUS=WARN; [ "$FAILS" -gt 0 ] && STATUS=FAIL

REPORT="$REPORT_DIR/$TS.md"
{
  echo "# Watchdog Report — $(date '+%Y-%m-%d %H:%M')"
  echo
  echo "**Status: $STATUS** — $FAILS fail / $WARNS warn / $OKS ok"
  echo
  for level in FAIL WARN OK; do
    grep "^$level|" "$RESULTS_FILE" | while IFS='|' read -r _ name msg; do
      case $level in FAIL) icon="🔴";; WARN) icon="🟡";; *) icon="🟢";; esac
      echo "- $icon **$name** — $msg"
    done
  done
} > "$REPORT"
ln -sf "$REPORT" "$REPORT_DIR/latest.md"

# Machine-readable status for the CCC dashboard / other consumers
{
  printf '{"ts":"%s","status":"%s","fails":%d,"warns":%d,"oks":%d,"checks":[' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$STATUS" "$FAILS" "$WARNS" "$OKS"
  first=1
  while IFS='|' read -r level name msg; do
    [ $first = 1 ] && first=0 || printf ','
    esc_msg=$(printf '%s' "$msg" | sed 's/\\/\\\\/g; s/"/\\"/g')
    printf '{"level":"%s","name":"%s","msg":"%s"}' "$level" "$name" "$esc_msg"
  done < "$RESULTS_FILE"
  printf ']}\n'
} > "$REPORT_DIR/latest-status.json"

# Notify on failures
if [ "$FAILS" -gt 0 ]; then
  TOP=$(grep '^FAIL|' "$RESULTS_FILE" | head -1 | cut -d'|' -f2-3 | tr '|' ': ')
  osascript -e "display notification \"$FAILS failing: $TOP\" with title \"Watchdog: $FAILS system(s) down\" sound name \"Basso\"" 2>/dev/null || true
fi

# Keep last 60 reports
ls -t "$REPORT_DIR"/*.md 2>/dev/null | grep -v latest.md | tail -n +61 | xargs rm -f 2>/dev/null || true

echo "watchdog: $STATUS ($FAILS fail / $WARNS warn / $OKS ok) -> $REPORT"
[ "$FAILS" -gt 0 ] && exit 1 || exit 0
