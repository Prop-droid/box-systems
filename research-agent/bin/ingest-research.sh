#!/bin/bash
# Research agent — external->internal ingest drafter.
# Turns a completed EXTERNAL research report into a reviewable PROPOSAL for wiki
# updates. Human-in-the-loop: it drafts to output/wiki-drafts/, never writes the wiki.
#
# Manual run:  bash ingest-research.sh <report-slug>     # one report
#              bash ingest-research.sh --all             # every report lacking a draft
# See ./README.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$(dirname "$SCRIPT_DIR")"
DRIVE="$HOME/Library/CloudStorage/GoogleDrive-propeidzas@gmail.com/My Drive"
CT="/home/tomas/brain"

RESEARCH_DIR="${RESEARCH_DIR:-/home/tomas/brain/systems/research-agent/output}"
WIKI_DIR="${WIKI_DIR:-$CT/wiki}"
RESEARCH_MODEL="${RESEARCH_MODEL:-claude-sonnet-4-6}"

REPORTS_DIR="$RESEARCH_DIR/reports"
DRAFTS_DIR="$RESEARCH_DIR/wiki-drafts"
LOGDIR="$AGENT_DIR/logs"
PROMPT_TEMPLATE="$SCRIPT_DIR/../prompts/ingest_prompt.txt"
mkdir -p "$DRAFTS_DIR" "$LOGDIR"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$PATH"
[ -f "$HOME/.hermes/.env" ] && { set -o allexport; source "$HOME/.hermes/.env"; set +o allexport; }
command -v claude >/dev/null || { echo "FAIL: claude CLI not on PATH"; exit 2; }

TODAY="$(date +%F)"

# Build the list of report slugs to process
slugs=()
if [ "${1:-}" = "--all" ]; then
  for r in "$REPORTS_DIR"/*.md; do
    [ -e "$r" ] || continue
    s="$(basename "$r" .md)"
    [ -f "$DRAFTS_DIR/$s-wiki-proposal.md" ] || slugs+=("$s")
  done
elif [ -n "${1:-}" ]; then
  slugs=("$1")
else
  echo "usage: ingest-research.sh <report-slug> | --all"; exit 1
fi

[ "${#slugs[@]}" -gt 0 ] || { echo "Nothing to ingest (all reports already drafted)."; exit 0; }

ingest_one() {
  local slug="$1"
  local report="$REPORTS_DIR/$slug.md"
  local out="$DRAFTS_DIR/$slug-wiki-proposal.md"
  [ -f "$report" ] || { echo "skip: no report $report"; return; }
  echo ">> ingest $slug"

  local rendered raw; rendered="$(mktemp)"; raw="$LOGDIR/_ingest-raw-$slug.md"
  python3 - "$PROMPT_TEMPLATE" "$rendered" "$report" "$WIKI_DIR" "$TODAY" <<'PY'
import sys, pathlib
tpl, out, report, wiki, today = sys.argv[1:6]
t = pathlib.Path(tpl).read_text()
for k, v in {"{{REPORT_PATH}}": report, "{{WIKI_DIR}}": wiki, "{{TODAY}}": today}.items():
    t = t.replace(k, v)
pathlib.Path(out).write_text(t)
PY

  if ! claude -p --model "$RESEARCH_MODEL" --dangerously-skip-permissions \
        --output-format text < "$rendered" > "$raw" 2>"$LOGDIR/_ingest-$slug.err"; then
    echo "   FAIL: claude errored (see _ingest-$slug.err)"; rm -f "$rendered"; return
  fi
  rm -f "$rendered"

  [ -s "$raw" ] || { echo "   FAIL: empty proposal"; return; }
  python3 - "$raw" "$out.tmp" <<'PY'
import sys, pathlib, re
t = pathlib.Path(sys.argv[1]).read_text()
i = t.find("\n# ")
t = t.lstrip() if t.lstrip().startswith("# ") else (t[i+1:] if i!=-1 else t)
t = t.replace(" — ", ", ").replace("—", ", ").replace("–", "-")
t = re.sub(r",\s*,", ",", t)
pathlib.Path(sys.argv[2]).write_text(t)
PY
  if [ ! -s "$out.tmp" ] || ! grep -qi "Wiki update proposal" "$out.tmp"; then
    echo "   FAIL: proposal malformed"; rm -f "$out.tmp"; return
  fi
  mv -f "$out.tmp" "$out"
  echo "   wrote $out ($(wc -l <"$out") lines)"
}

for s in "${slugs[@]}"; do ingest_one "$s"; done
echo "ingest done."
