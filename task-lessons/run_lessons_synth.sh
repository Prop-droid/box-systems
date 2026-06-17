#!/bin/bash
# Task-lessons synthesis: cluster un-promoted lesson records, find stable patterns
# (>= 3 consistent), and write gated promotion proposals (proposals.jsonl + .md).
# NEVER writes to canon — promotion is a separate, human-gated step.
#
# Run manually:  bash run_lessons_synth.sh
# Activate weekly once a lesson pool exists (>= ~2 weeks of captures): add a
# systemd timer or cron entry on the box that runs this. Safe + idempotent on an
# empty/already-synthesized ledger (promoted flag, not a timestamp).
set -uo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$HOME/.bun/bin:$PATH"

DIR="$HOME/sha-systems/task-lessons"
LOG_DIR="$DIR/logs"
mkdir -p "$LOG_DIR"
TS="$(date +%Y-%m-%d_%H%M%S)"
LOG="$LOG_DIR/synth-$TS.log"
exec >>"$LOG" 2>&1
echo "=== task-lessons synth $TS ==="
cd "$DIR" || { echo "ERROR: cannot cd to $DIR"; exit 1; }
# shellcheck source=/dev/null
[ -f "$DIR/../lib/hermes_fallback.sh" ] && . "$DIR/../lib/hermes_fallback.sh"

LESSONS="$(python3 unpromoted.py 2>>"$LOG")"
if [ -z "$LESSONS" ]; then
  echo "Nothing to synthesize (no un-promoted lessons)."
  printf '' > "$DIR/proposals.jsonl"
  printf 'No stable patterns yet (need >= 3 consistent lessons per pattern).\n' > "$DIR/proposals.md"
  exit 0
fi

PROMPT_TMP="$(mktemp)"
{ cat synth_prompt.md; echo; echo "=== LESSON RECORDS ==="; echo "$LESSONS"; } > "$PROMPT_TMP"

echo ">> claude -p (generating proposals.jsonl)"
OUT_TMP="$(mktemp)"; ok=0
if claude -p --model claude-sonnet-4-6 --output-format text < "$PROMPT_TMP" > "$OUT_TMP" 2>"$DIR/_claude.err"; then
  ok=1
elif command -v hermes_fallback >/dev/null 2>&1 && hermes_fallback "$PROMPT_TMP" "$OUT_TMP" "$DIR/_claude.err"; then
  ok=1; echo ">> recovered via hermes"
fi

if [ "$ok" = 1 ]; then
  # Keep only well-formed JSON lines (defensive against stray prose).
  python3 -c 'import json,sys
for l in sys.stdin:
    l=l.strip()
    if not l: continue
    try: json.loads(l)
    except Exception: continue
    print(l)' < "$OUT_TMP" > "$DIR/proposals.jsonl"
  python3 render_proposals_md.py < "$DIR/proposals.jsonl" > "$DIR/proposals.md"
  echo "=== done $TS — $(wc -l < "$DIR/proposals.jsonl" | tr -d ' ') proposal(s) ==="
else
  echo "FAILED: claude -p and hermes fallback both failed (see _claude.err)"
  rm -f "$OUT_TMP" "$PROMPT_TMP"; exit 1
fi
rm -f "$OUT_TMP" "$PROMPT_TMP"
