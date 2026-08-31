#!/bin/bash
# Feedback synthesis: cluster un-promoted creative records + un-promoted decision
# disagreements; write structured proposals.jsonl (primary) and a proposals.md
# digest. Used by the Monday cron and the in-app "Run synthesis" button.
# NEVER writes to canon — promotion is gated and handled separately.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$PATH"

DIR="$HOME/systems/creative-feedback"
LOG_DIR="$HOME/Library/Logs/creative-feedback"
mkdir -p "$LOG_DIR"
TS="$(date +%Y-%m-%d_%H%M%S)"
LOG="$LOG_DIR/$TS.log"
exec >>"$LOG" 2>&1
echo "=== feedback synth $TS ==="
cd "$DIR" || { echo "ERROR: cannot cd to $DIR"; exit 1; }

# Override log default matches the CCC config (config.overrideLog absolute form).
export OVERRIDE_LOG="${OVERRIDE_LOG:-$HOME/creative-command-center/.cache/overrides.jsonl}"
export FEEDBACK_DIR="$DIR"

CREATIVE="$(python3 unpromoted.py 2>>"$LOG")"
DECISIONS="$(python3 decisions_unpromoted.py 2>>"$LOG")"

if [ -z "$CREATIVE" ] && [ -z "$DECISIONS" ]; then
  echo "Nothing to synthesize (no un-promoted records)."
  printf '' > "$DIR/proposals.jsonl"
  printf 'No stable patterns yet (need >= 3 consistent records per pattern).\n' > "$DIR/proposals.md"
  exit 0
fi

PROMPT_TMP="$(mktemp)"
{
  cat synth_prompt.md
  echo
  echo "=== CREATIVE RECORDS ==="
  echo "$CREATIVE"
  echo
  echo "=== DECISION DISAGREEMENTS ==="
  echo "$DECISIONS"
} > "$PROMPT_TMP"

echo ">> claude -p (generating proposals.jsonl)"
OUT_TMP="$(mktemp)"
if claude -p --model claude-sonnet-4-6 --output-format text < "$PROMPT_TMP" > "$OUT_TMP" 2>"$DIR/_claude.err"; then
  # Keep only well-formed JSON lines (defensive against stray prose).
  python3 -c 'import json,sys
for l in sys.stdin:
    l=l.strip()
    if not l: continue
    try: json.loads(l)
    except Exception: continue
    print(l)' < "$OUT_TMP" > "$DIR/proposals.jsonl"
  python3 render_proposals_md.py < "$DIR/proposals.jsonl" > "$DIR/proposals.md"
  N=$(wc -l < "$DIR/proposals.jsonl" | tr -d ' ')
  echo "=== done $TS — $N proposal(s) ==="
  # Close the loop: proposals used to land silently in proposals.md and rot.
  # Post the digest where Tomas decides; verdict-miner records his reply.
  if [ "$N" -gt 0 ]; then
    { echo "🧪 **Feedback synth — $N pattern proposal(s) awaiting your verdict**"
      head -c 1400 "$DIR/proposals.md"
      echo
      echo "Approve/reject: http://100.107.26.69:3000/feedback — or reply here."
    } | bash "$HOME/systems/lib/discord-post.sh" 1531648564932120737 CREATIVE_TOKEN || \
      echo "WARN: #creative digest post failed"
  fi
else
  echo "FAILED: claude -p (see _claude.err)"
  rm -f "$OUT_TMP" "$PROMPT_TMP"
  exit 1
fi
rm -f "$OUT_TMP" "$PROMPT_TMP"
