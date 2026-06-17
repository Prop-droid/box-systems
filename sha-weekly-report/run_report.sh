#!/bin/bash
# SHA weekly brand-health report
# Runs every Monday at 09:07 Europe/Vilnius via ~/Library/LaunchAgents/com.tomas.sha-weekly-report.plist
# See ./README.md for design / queries / prompt.
#
# Manual run: bash run_report.sh [YYYY-MM-DD-of-last-monday]
#   no arg = compute last Mon→Sun automatically

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRIVE="$HOME/Library/CloudStorage/GoogleDrive-propeidzas@gmail.com/My Drive"
PROJ_ROOT="/home/tomas/brain/projects"

# Load env (BQ creds, project, dataset)
if [ -f "$HOME/.hermes/.env" ]; then
  set -o allexport
  source "$HOME/.hermes/.env"
  set +o allexport
fi
export GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS/#\~/$HOME}"

# Make sure bq and claude CLIs are on PATH (launchd has minimal PATH)
export PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Cellar:$HOME/.local/bin:$PATH"

# Compute date ranges
if [ "${1:-}" != "" ]; then
  ANCHOR_MON="$1"
  read LAST_FROM LAST_TO PRIOR_FROM PRIOR_TO ROLLING_FROM ROLLING_TO REPORT_MONTH < <(
    python3 - "$ANCHOR_MON" <<'PY'
import sys
from datetime import date, timedelta, datetime
anchor = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
# anchor is the Monday of the week being reported
last_start = anchor
last_end = anchor + timedelta(days=6)
prior_end = last_start - timedelta(days=1)
prior_start = prior_end - timedelta(days=6)
rolling_end = prior_end
rolling_start = rolling_end - timedelta(days=27)
print(last_start, last_end, prior_start, prior_end, rolling_start, rolling_end, date.today().strftime("%Y-%m"))
PY
  )
else
  read LAST_FROM LAST_TO PRIOR_FROM PRIOR_TO ROLLING_FROM ROLLING_TO REPORT_MONTH < <(
    python3 - <<'PY'
from datetime import date, timedelta
today = date.today()
last_end = today - timedelta(days=today.weekday() + 1)   # previous Sunday
last_start = last_end - timedelta(days=6)                # previous Monday
prior_end = last_start - timedelta(days=1)
prior_start = prior_end - timedelta(days=6)
rolling_end = prior_end
rolling_start = rolling_end - timedelta(days=27)
print(last_start, last_end, prior_start, prior_end, rolling_start, rolling_end, today.strftime("%Y-%m"))
PY
  )
fi

# Nested layout (migrated 2026-06-09): projects/<YYYY-MM>/sha-weekly-report/<week-start>/
OUTDIR="$PROJ_ROOT/$REPORT_MONTH/sha-weekly-report/$LAST_FROM"
mkdir -p "$OUTDIR"
LOG="$OUTDIR/_run.log"

# All stdout/stderr below goes to log; also echoed when run interactively
exec > >(tee -a "$LOG") 2>&1

echo "==============================================="
echo "[$(date)] SHA weekly report"
echo "  Week:       $LAST_FROM to $LAST_TO"
echo "  Prior:      $PRIOR_FROM to $PRIOR_TO"
echo "  4-wk base:  $ROLLING_FROM to $ROLLING_TO"
echo "  Output:     $OUTDIR"
echo "==============================================="

# Sanity checks
command -v bq >/dev/null || { echo "FAIL: bq CLI not on PATH ($PATH)"; exit 2; }
command -v claude >/dev/null || { echo "FAIL: claude CLI not on PATH"; exit 2; }
[ -f "$GOOGLE_APPLICATION_CREDENTIALS" ] || { echo "FAIL: SA file not found at $GOOGLE_APPLICATION_CREDENTIALS"; exit 2; }

# Run each query, substituting placeholders
run_query() {
  local sql_file="$1"
  local out_name="$(basename "$sql_file" .sql)"
  echo ">> $out_name.sql"
  # Render placeholders, then pipe via stdin so bq doesn't try to parse leading -- comments as flags
  sed \
    -e "s|{{LAST_FROM}}|$LAST_FROM|g" \
    -e "s|{{LAST_TO}}|$LAST_TO|g" \
    -e "s|{{PRIOR_FROM}}|$PRIOR_FROM|g" \
    -e "s|{{PRIOR_TO}}|$PRIOR_TO|g" \
    -e "s|{{ROLLING_FROM}}|$ROLLING_FROM|g" \
    -e "s|{{ROLLING_TO}}|$ROLLING_TO|g" \
    "$sql_file" \
  | bq query --use_legacy_sql=false --format=pretty --max_rows=25 \
    > "$OUTDIR/$out_name.txt" 2>"$OUTDIR/$out_name.err" || {
      echo "WARN: $out_name failed (see $out_name.err); continuing"
    }
}

for q in "$SCRIPT_DIR/queries/"*.sql; do
  run_query "$q"
done

# Assemble the prompt + data bundle (Python handles multiline values cleanly)
PROMPT_TEMPLATE="$SCRIPT_DIR/report_prompt.txt"
python3 - "$PROMPT_TEMPLATE" "$OUTDIR/_assembled_prompt.txt" \
  "$LAST_FROM" "$LAST_TO" "$PRIOR_FROM" "$PRIOR_TO" "$ROLLING_FROM" "$ROLLING_TO" \
  "$OUTDIR/01_topline.txt" "$OUTDIR/02_channels.txt" \
  "$OUTDIR/03_top_spend.txt" "$OUTDIR/04_top_roas.txt" \
  "$OUTDIR/05_losers.txt" "$OUTDIR/06_angles.txt" \
  "$OUTDIR/07_landing_pages.txt" "$OUTDIR/08_funnel.txt" "$OUTDIR/09_creative_funnel.txt" \
  "$OUTDIR/10_hook_hold.txt" "$OUTDIR/11_fatigue.txt" "$OUTDIR/12_concepts.txt" <<'PY'
import sys, pathlib
(prompt_tpl, out_prompt,
 lf, lt, pf, pt, rf, rt,
 topline, channels, top_spend, top_roas, losers, angles,
 landing_pages, funnel, creative_funnel,
 hook_hold, fatigue, concepts) = sys.argv[1:]

def read(p):
    try:
        return pathlib.Path(p).read_text()
    except Exception:
        return "(no data)"

subs = {
    "{{LAST_FROM}}": lf, "{{LAST_TO}}": lt,
    "{{PRIOR_FROM}}": pf, "{{PRIOR_TO}}": pt,
    "{{ROLLING_FROM}}": rf, "{{ROLLING_TO}}": rt,
    "{{TOPLINE_TABLE}}": read(topline),
    "{{CHANNELS_TABLE}}": read(channels),
    "{{TOP_SPEND_TABLE}}": read(top_spend),
    "{{TOP_ROAS_TABLE}}": read(top_roas),
    "{{LOSERS_TABLE}}": read(losers),
    "{{ANGLES_TABLE}}": read(angles),
    "{{LANDING_PAGES_TABLE}}": read(landing_pages),
    "{{FUNNEL_TABLE}}": read(funnel),
    "{{CREATIVE_FUNNEL_TABLE}}": read(creative_funnel),
    "{{HOOK_HOLD_TABLE}}": read(hook_hold),
    "{{FATIGUE_TABLE}}": read(fatigue),
    "{{CONCEPTS_TABLE}}": read(concepts),
}
text = pathlib.Path(prompt_tpl).read_text()
for k, v in subs.items():
    text = text.replace(k, v)
pathlib.Path(out_prompt).write_text(text)
PY

# Call claude CLI in print mode with Sonnet (cheap fetch-and-write task).
# Write to a LOCAL temp file (streaming straight onto a Drive/FileProvider path
# produced truncated output on 2026-06-10: file started mid-table, no H1).
# Retry up to 3 attempts; each attempt must be non-empty AND contain an H1.
echo ">> claude -p (generating report.md)"
RAW_TMP="$(mktemp /tmp/sha-weekly-raw.XXXXXX)"
CLAUDE_OK=0
for attempt in 1 2 3; do
  : > "$RAW_TMP"
  if claude -p --model claude-sonnet-4-6 --output-format text < "$OUTDIR/_assembled_prompt.txt" > "$RAW_TMP" 2>"$OUTDIR/_claude.err"; then
    if [ -s "$RAW_TMP" ] && grep -q "^# " "$RAW_TMP"; then
      CLAUDE_OK=1
      break
    fi
    echo "WARN: attempt $attempt produced invalid output ($(wc -c <"$RAW_TMP") bytes, H1 $(grep -q '^# ' "$RAW_TMP" && echo present || echo missing)) — retrying"
  else
    echo "WARN: attempt $attempt — claude CLI errored (see _claude.err) — retrying"
  fi
  sleep 15
done
if [ "$CLAUDE_OK" != "1" ]; then
  echo "FAIL: claude output invalid after 3 attempts — keeping previous report.md"
  cp -f "$RAW_TMP" "$OUTDIR/_report_raw.md" 2>/dev/null || true
  rm -f "$RAW_TMP"
  exit 3
fi
cp -f "$RAW_TMP" "$OUTDIR/_report_raw.md"
rm -f "$RAW_TMP"

# Strip any preamble before the first markdown H1 -> write to a TEMP file first
python3 - "$OUTDIR/_report_raw.md" "$OUTDIR/report.md.tmp" <<'PY'
import sys, pathlib
src, dst = sys.argv[1], sys.argv[2]
text = pathlib.Path(src).read_text()
i = text.find("\n# ")
if i == -1 and text.lstrip().startswith("# "):
    cleaned = text.lstrip()
elif i != -1:
    cleaned = text[i+1:]
else:
    cleaned = text
pathlib.Path(dst).write_text(cleaned)
PY

# Sanity-check the TEMP file; only promote to report.md if it passes, so a flaky
# run never overwrites a good prior report with an empty/malformed one.
if [ ! -s "$OUTDIR/report.md.tmp" ] || ! grep -q "Shameless Snacks" "$OUTDIR/report.md.tmp"; then
  echo "FAIL: new report empty or malformed — keeping previous report.md"
  rm -f "$OUTDIR/report.md.tmp"
  exit 4
fi
mv -f "$OUTDIR/report.md.tmp" "$OUTDIR/report.md"

echo "[$(date)] DONE: $OUTDIR/report.md ($(wc -l <"$OUTDIR/report.md") lines)"
