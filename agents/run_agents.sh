#!/bin/bash
# Agent cron suite: runs maintenance agents headless via claude CLI.
#   run_agents.sh weekly   -> transcript janitor (bash), compiler lint (bash),
#                             memory-hygiene, skill-garden, retro (claude agents)
#   run_agents.sh monthly  -> consolidation, token-audit (claude agents)
# Prompts live in prompts/<name>.md; each agent's stdout becomes its report in
# reports/<name>/YYYY-MM-DD.md. Agents run on Sonnet (cap discipline); prompt
# goes via STDIN — --allowed-tools is variadic and eats positional prompts.
set -uo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$HOME/.bun/bin:$PATH"
AG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LANE="${1:-weekly}"
TODAY="$(date +%Y-%m-%d)"
LOG_DIR="$HOME/Library/Logs/agents-$LANE"
mkdir -p "$LOG_DIR"
exec >>"$LOG_DIR/$TODAY.log" 2>&1
echo "=== agents $LANE $(date) ==="

CLAUDE_BIN="/usr/local/bin/claude-max"
MODEL="claude-sonnet-4-6"
SUMMARY=()

TL_DIR="$AG_DIR/../task-lessons"
# shellcheck source=/dev/null
[ -f "$AG_DIR/../lib/hermes_fallback.sh" ] && . "$AG_DIR/../lib/hermes_fallback.sh"

run_claude_agent() {
  local name=$1
  local prompt="$AG_DIR/prompts/$name.md"
  local out_dir="$AG_DIR/reports/$name"
  mkdir -p "$out_dir"
  local out="$out_dir/$TODAY.md"
  echo "--- agent: $name ---"
  if [ ! -f "$prompt" ]; then echo "MISSING PROMPT $prompt"; SUMMARY+=("$name: missing prompt"); return 1; fi

  # task-lessons RECALL: prime the prompt with this agent's own past lessons.
  local infile="$prompt"
  if [ -x "$TL_DIR/recall.sh" ]; then
    local lessons; lessons="$("$TL_DIR/recall.sh" "$name" 5 2>/dev/null || true)"
    if [ -n "$lessons" ]; then
      infile="$(mktemp)"
      { printf '%s\n\n' "$lessons"; cat "$prompt"; } > "$infile"
      echo "primed with $(printf '%s\n' "$lessons" | grep -c '^- ') past lesson(s)"
    fi
  fi

  # env = no-op wrapper; macOS bash 3.2 + set -u chokes on empty-array expansion
  local timeout_cmd=(env)
  command -v gtimeout >/dev/null && timeout_cmd=(gtimeout 1500); command -v timeout >/dev/null && timeout_cmd=(timeout 1500)
  local rc=0 via=claude start=$SECONDS
  if "${timeout_cmd[@]}" "$CLAUDE_BIN" --print --model "$MODEL" \
        --dangerously-skip-permissions \
        --allowed-tools "Read Write Edit Bash Glob Grep Skill" \
        < "$infile" > "$out" 2>"$out_dir/$TODAY.err"; then
    echo "OK -> $out ($(wc -l < "$out" | tr -d ' ') lines)"
    SUMMARY+=("$name: ok")
  elif command -v hermes_fallback >/dev/null 2>&1 && \
       hermes_fallback "$infile" "$out" "$out_dir/$TODAY.err"; then
    via=hermes
    echo "OK via hermes -> $out ($(wc -l < "$out" | tr -d ' ') lines)"
    SUMMARY+=("$name: ok(hermes)")
  else
    rc=$?
    echo "FAILED (see $out_dir/$TODAY.err)"
    SUMMARY+=("$name: FAILED")
  fi
  [ "$infile" != "$prompt" ] && rm -f "$infile"

  # task-lessons CAPTURE: record the outcome (best-effort; never alters the run).
  # A hermes rescue is logged as 'fixed' so the loop learns where claude is flaky.
  if [ -f "$TL_DIR/lib.sh" ]; then
    # shellcheck source=/dev/null
    . "$TL_DIR/lib.sh"
    if [ "$via" = hermes ]; then
      lessons_capture --skill "$name" --exit 0 --verdict fixed \
        --duration "$((SECONDS - start))" --log "$out_dir/$TODAY.err" \
        --lesson "claude -p failed for $name; hermes fallback recovered the run" \
        --how "if this recurs, check the $name prompt/tools against claude headless limits" || true
    else
      lessons_capture --skill "$name" --exit "$rc" --duration "$((SECONDS - start))" \
        --log "$out_dir/$TODAY.err" || true
    fi
  fi
}

if [ "$LANE" = "weekly" ]; then
  echo "--- transcript janitor ---"
  bash "$AG_DIR/../transcript-janitor/run_janitor.sh" && SUMMARY+=("janitor: ok") || SUMMARY+=("janitor: FAILED")


  run_claude_agent memory-hygiene
  run_claude_agent skill-garden
  run_claude_agent retro      # last: reads the other reports from today
elif [ "$LANE" = "monthly" ]; then
  run_claude_agent consolidation
  run_claude_agent token-audit
else
  echo "unknown lane: $LANE"; exit 1
fi

MSG=$(IFS='; '; echo "${SUMMARY[*]}")
echo "summary: $MSG"
osascript -e "display notification \"$MSG\" with title \"Agents ($LANE) done\"" 2>/dev/null || true
echo "=== done $(date) ==="
