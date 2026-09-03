#!/bin/bash
# mechanism-tagger: nightly LLM (haiku) tagging of competitor ads + SHA winners with
# buying-psychology devices -> $RESEARCH_DIR/mechanisms/tags.json (read by CCC Intel).
# Scheduled by mechanism-tagger.timer (daily 02:15, after the 01:45 Atria pull).
# Manual: bash run.sh [--dry-run|--force|--limit N]
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$SCRIPT_DIR/run.log"

export PATH="$HOME/.local/bin:$HOME/.bun/bin:/usr/local/bin:$PATH"
# CCC's .env.local is the source of truth for the data paths; reuse it so the
# tagger and the dashboard can never disagree on which files they read.
if [ -f "$HOME/creative-command-center/.env.local" ]; then
  set -o allexport; source "$HOME/creative-command-center/.env.local"; set +o allexport
fi

command -v claude >/dev/null || { echo "FAIL: claude CLI not on PATH" | tee -a "$LOG"; exit 2; }

{
  echo "=== mechanism-tagger $(date '+%Y-%m-%d %H:%M') ==="
  python3 "$SCRIPT_DIR/tag.py" "$@"
  rc=$?
  echo "exit $rc"
  exit $rc
} 2>&1 | tee -a "$LOG"
exit "${PIPESTATUS[0]}"
