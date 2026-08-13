#!/bin/bash
# Self-improve digest: gather the newest report from every proposal-generating
# agent (retro, skill-garden, memory-hygiene, task-lessons, creative-feedback,
# monthly consolidation/token-audit), distill into ONE ranked pending.md, and
# post it to Discord so the proposals actually reach Tomas.
#
# This is the last mile of the self-learning loop: the sources already run
# weekly but their reports died unread in ~/systems/agents/reports/. Promotion
# stays human-gated: Tomas replies in #dev "self-improve: apply P2, P4" and the
# dispatched session applies exactly those items (protocol in pending.md header
# and memory/project_self_improve_loop.md).
#
# Manual run: bash run_digest.sh   (burns Claude window tokens, posts to Discord)
set -uo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$HOME/.bun/bin:$PATH"

DIR="$HOME/systems/self-improve"
SYS="$HOME/systems"
LOG_DIR="$DIR/logs"
mkdir -p "$LOG_DIR" "$DIR/archive"
TS="$(date +%Y-%m-%d_%H%M%S)"
TODAY="$(date +%Y-%m-%d)"
LOG="$LOG_DIR/digest-$TS.log"
exec >>"$LOG" 2>&1
echo "=== self-improve digest $TS ==="
START=$SECONDS
# shellcheck source=/dev/null
[ -f "$SYS/lib/hermes_fallback.sh" ] && . "$SYS/lib/hermes_fallback.sh"

MAX_AGE_DAYS=8          # weekly sources; monthly ones only included when fresh
CLAUDE_BIN="/usr/local/bin/claude-max"
MODEL="claude-sonnet-4-6"

# newest_report <dir> [max_age_days] -> path or empty
newest_report() {
  local d="$1" age="${2:-$MAX_AGE_DAYS}"
  find "$d" -maxdepth 1 -name '*.md' -mtime "-$age" 2>/dev/null | sort | tail -1
}

PROMPT_TMP="$(mktemp)"
cat "$DIR/digest_prompt.md" > "$PROMPT_TMP"
blocks=0
add_block() {  # add_block <label> <file>
  [ -n "$2" ] && [ -s "$2" ] || return 0
  { echo; echo "=== $1 ($(basename "$2")) ==="; cat "$2"; } >> "$PROMPT_TMP"
  blocks=$((blocks+1))
  echo "included: $1 <- $2"
}

add_block "WEEKLY RETRO"       "$(newest_report "$SYS/agents/reports/retro")"
add_block "SKILL GARDEN"       "$(newest_report "$SYS/agents/reports/skill-garden")"
add_block "MEMORY HYGIENE"     "$(newest_report "$SYS/agents/reports/memory-hygiene")"
add_block "CONSOLIDATION (monthly)" "$(newest_report "$SYS/agents/reports/consolidation" 32)"
add_block "TOKEN AUDIT (monthly)"   "$(newest_report "$SYS/agents/reports/token-audit" 32)"
add_block "SKILL TELEMETRY"         "$(newest_report "$SYS/skill-telemetry/reports")"
add_block "TASK-LESSONS PROPOSALS"     "$SYS/task-lessons/proposals.md"
add_block "CREATIVE-FEEDBACK PROPOSALS" "$SYS/creative-feedback/proposals.md"

if [ "$blocks" -eq 0 ]; then
  echo "no fresh source reports; nothing to digest"
  rm -f "$PROMPT_TMP"
  exit 0
fi

# Archive last week's pending list before overwriting.
[ -s "$DIR/pending.md" ] && cp "$DIR/pending.md" "$DIR/archive/pending-$(date -r "$DIR/pending.md" +%Y-%m-%d).md"

OUT_TMP="$(mktemp)"
ok=0
for attempt in 1 2 3; do
  echo ">> claude-max attempt $attempt"
  if timeout 1500 "$CLAUDE_BIN" --print --model "$MODEL" \
       --dangerously-skip-permissions --allowed-tools "Read Glob Grep" \
       < "$PROMPT_TMP" > "$OUT_TMP" 2>"$DIR/_claude.err" \
     && [ -s "$OUT_TMP" ] && head -1 "$OUT_TMP" | grep -q '^# '; then
    ok=1; break
  fi
  sleep 30
done
if [ "$ok" = 0 ] && command -v hermes_fallback >/dev/null 2>&1 \
   && hermes_fallback "$PROMPT_TMP" "$OUT_TMP" "$DIR/_claude.err" \
   && [ -s "$OUT_TMP" ] && head -1 "$OUT_TMP" | grep -q '^# '; then
  ok=1; echo ">> recovered via hermes"
fi

RC=0
if [ "$ok" = 1 ]; then
  mv "$OUT_TMP" "$DIR/pending.md"
  N="$(grep -c '^### P' "$DIR/pending.md" || true)"
  BODY="$N open proposal(s) from $blocks source report(s).
$(grep '^### P' "$DIR/pending.md" | head -3 | sed 's/^### /• /')
Full list: ~/systems/self-improve/pending.md
Reply here: \"self-improve: apply P2, P4\" (or skip)."
  bash "$SYS/lib/discord-notify.sh" "Self-improve digest $TODAY" "$BODY" default
  echo "=== done $TS — $N proposal(s), posted to Discord ==="
else
  # Deterministic fallback: degrade to a pointer message, never to silence.
  RC=1
  echo "FAILED: claude and hermes both failed (see _claude.err)"
  bash "$SYS/lib/discord-notify.sh" "Self-improve digest $TODAY: synth FAILED" \
    "LLM digest failed; $blocks raw report(s) ready under ~/systems/agents/reports/ and */proposals.md. See $LOG" high
  rm -f "$OUT_TMP"
fi
rm -f "$PROMPT_TMP"

# shellcheck source=/dev/null
if [ -f "$SYS/task-lessons/lib.sh" ]; then
  . "$SYS/task-lessons/lib.sh"
  lessons_capture --skill "self-improve-digest" --exit "$RC" \
    --duration "$((SECONDS-START))" --log "$LOG" || true
fi
exit "$RC"
