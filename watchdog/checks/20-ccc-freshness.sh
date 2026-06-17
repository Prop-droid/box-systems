#!/bin/bash
# CCC steward: data-freshness checks for creative-command-center.
# Reads paths from the app's .env.local so env drift is caught immediately.
set -uo pipefail
WD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$WD_DIR/lib/common.sh"

CCC="$HOME/creative-command-center"
ENVF="$CCC/.env.local"

if [ ! -f "$ENVF" ]; then
  fail "ccc:env" ".env.local missing at $ENVF"
  exit 0
fi
envval() { grep "^$1=" "$ENVF" | head -1 | cut -d= -f2-; }

# Credentials the app depends on
for pair in "GOOGLE_APPLICATION_CREDENTIALS:BQ service account" "CLICKUP_TOKEN_FILE:ClickUp token"; do
  key=${pair%%:*}; desc=${pair#*:}
  p=$(envval "$key")
  if [ -s "$p" ]; then ok "ccc:cred-$key" "$desc present"
  else fail "ccc:cred-$key" "$desc missing/empty: $p"; fi
done

# winners.jsonl: fresh (weekly refresh + 2d slack) and non-trivial
W=$(envval WINNERS_JSONL)
if [ -f "$W" ]; then
  age=$(age_hours "$(newest_mtime_epoch "$W")")
  lines=$(wc -l < "$W" | tr -d ' ')
  if [ "$age" -gt 216 ]; then fail "ccc:winners" "winners.jsonl ${age}h old (refresh cron dead?)"
  elif [ "$lines" -lt 300 ]; then warn "ccc:winners" "winners.jsonl only $lines lines (expected 300+)"
  else ok "ccc:winners" "$lines winners, ${age}h old"; fi
else fail "ccc:winners" "winners.jsonl missing: $W"; fi

# SWIPE_DIR: must contain images (env drifted once before -> tab showed 0).
# head -50 early-exits the find (SIGPIPE) — unbounded scans over Drive
# FileProvider trees timed out the whole check under launchd (2026-06-10).
S=$(envval SWIPE_DIR)
imgs=$(find "$S" -type f \( -name '*.jpg' -o -name '*.jpeg' -o -name '*.png' -o -name '*.webp' -o -name '*.gif' \) 2>/dev/null | head -50 | wc -l | tr -d ' ')
if [ "${imgs:-0}" -gt 0 ]; then ok "ccc:swipe-dir" "$imgs+ images in SWIPE_DIR"
else fail "ccc:swipe-dir" "0 images in SWIPE_DIR ($S) — path drift?"; fi

# ATRIA_DIR: monitor writes daily JSONL
A=$(envval ATRIA_DIR)
age=$(age_hours "$(newest_mtime_epoch "$A"/*.jsonl)")
if [ "$age" -le 48 ]; then ok "ccc:atria" "newest atria pull ${age}h old"
else fail "ccc:atria" "no atria JSONL for ${age}h (research-monitor dead or path drift: $A)"; fi

# RESEARCH_DIR: feed + reports
R=$(envval RESEARCH_DIR)
age=$(age_hours "$(newest_mtime_epoch "$R"/feed/*.jsonl)")
if [ "$age" -le 48 ]; then ok "ccc:research-feed" "feed ${age}h old"
else fail "ccc:research-feed" "research feed ${age}h old ($R/feed)"; fi
age=$(age_hours "$(newest_mtime_epoch "$R"/reports/*.md)")
if [ "$age" -le 192 ]; then ok "ccc:research-reports" "newest deep-dive ${age}h old"
else warn "ccc:research-reports" "no new deep-dive report for ${age}h"; fi

# Comments digest: weekly (Tue) AI digest the CCC /comments page serves
CD="$HOME/systems/comments-digest/out"
age=$(age_hours "$(newest_mtime_epoch "$CD"/digest-*.md)")
if [ "$age" -le 216 ]; then ok "ccc:comments-digest" "newest digest ${age}h old"
else warn "ccc:comments-digest" "no comments digest for ${age}h (cron dead or never ran)"; fi

# Weekly report: nested layout projects/<month>/sha-weekly-report/<date>/report.md (+ legacy flat).
# Only scan the current + previous month dirs — a full projects-tree find over
# Drive FileProvider exceeded the 300s check cap under launchd (2026-06-10).
PROJ="/home/tomas/brain/projects"
THIS_M=$(date +%Y-%m)
PREV_M=$(date -d "-1 month" +%Y-%m)
newest=0
for mdir in "$PROJ/$THIS_M" "$PROJ/$PREV_M"; do
  [ -d "$mdir" ] || continue
  while IFS= read -r f; do
    m=$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null) || continue
    [ "$m" -gt "$newest" ] && newest=$m
  done < <(find "$mdir" -maxdepth 3 -path '*sha-weekly-report*' -name 'report.md' 2>/dev/null | head -20)
done
age=$(age_hours "$newest")
if [ "$age" -le 216 ]; then ok "ccc:weekly-report" "newest report.md ${age}h old"
else fail "ccc:weekly-report" "newest weekly report.md ${age}h old — cron dead or layout moved"; fi
