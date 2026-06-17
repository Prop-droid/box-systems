#!/bin/bash
# Research agent — deep-dive worker.
# Drains ONE pending question from the queue, runs a headless creative-strategy
# research pass, writes a brief-ready report the Command Center /research tab reads.
#
# Manual run:  bash deepdive.sh            # processes the next pending question
#              bash deepdive.sh --dry-run  # show what it would pick, do nothing
#
# Scheduled via ~/Library/LaunchAgents/com.tomas.research-deepdive.plist
# See ./README.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$(dirname "$SCRIPT_DIR")"
DRIVE="$HOME/Library/CloudStorage/GoogleDrive-propeidzas@gmail.com/My Drive"
CT="/home/tomas/brain"

# --- config (env-overridable) ---
RESEARCH_DIR="${RESEARCH_DIR:-/home/tomas/brain/systems/research-agent/output}"
# Research is EXTERNAL-only (web + competitor ads). The internal wiki is the
# destination for findings, NOT a research input — so it is intentionally not read.
SWIPE_DIR="${SWIPE_DIR:-$CT/projects/2026-06/competitor-ads-scrape}"
RESEARCH_MODEL="${RESEARCH_MODEL:-claude-sonnet-4-6}"
RESEARCH_TIMEOUT="${RESEARCH_TIMEOUT:-1500}"   # seconds; headless research can take a while

QUEUE="$RESEARCH_DIR/queue.jsonl"
REPORTS_DIR="$RESEARCH_DIR/reports"
FEED_DIR="$RESEARCH_DIR/feed"
STATE_DIR="$RESEARCH_DIR/state"
LOGDIR="$AGENT_DIR/logs"
PROMPTS_DIR="$SCRIPT_DIR/../prompts"
mkdir -p "$REPORTS_DIR" "$FEED_DIR" "$STATE_DIR" "$LOGDIR"

# launchd has a minimal PATH; make CLIs reachable
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$PATH"
[ -f "$HOME/.hermes/.env" ] && { set -o allexport; source "$HOME/.hermes/.env"; set +o allexport; }

TODAY="$(date +%F)"
LOG="$LOGDIR/deepdive-$TODAY.log"
exec > >(tee -a "$LOG") 2>&1
TEE_PID=$!
RENDERED=""
TL_DIR="$AGENT_DIR/../task-lessons"   # task-lessons loop
STARTED=0; RUN_START=0; VIA=claude     # set around the claude run
# shellcheck source=/dev/null
[ -f "$AGENT_DIR/../lib/hermes_fallback.sh" ] && . "$AGENT_DIR/../lib/hermes_fallback.sh"
# Single EXIT trap: capture the run as a lesson (best-effort, only if a research
# run was actually launched), clean temp file, close stdout/stderr so tee gets
# EOF, then wait for it — otherwise the last log lines race the exit and vanish.
cleanup() {
  local rc=$?
  if [ "$STARTED" = "1" ] && [ -f "$TL_DIR/lib.sh" ]; then
    local -a vargs=(--exit "$rc")
    [ "$VIA" = hermes ] && vargs=(--exit 0 --verdict fixed \
      --lesson "claude -p failed for research-deepdive; hermes fallback recovered the run" \
      --how "if recurring, check the deepdive prompt/tools against claude headless limits")
    ( . "$TL_DIR/lib.sh"
      lessons_capture --skill "research-deepdive" "${vargs[@]}" \
        --duration "$((SECONDS - RUN_START))" \
        --log "$LOGDIR/_claude-${SLUG:-unknown}.err" \
        --link "memory/project_research_agent" ) || true
  fi
  [ -n "$RENDERED" ] && rm -f "$RENDERED"; exec 1>&- 2>&-; [ -n "${TEE_PID:-}" ] && wait "$TEE_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "=================================================="
echo "[$(date)] research deep-dive"
echo "  queue:   $QUEUE"
echo "  model:   $RESEARCH_MODEL"
echo "=================================================="

command -v claude >/dev/null || { echo "FAIL: claude CLI not on PATH"; exit 2; }
[ -f "$QUEUE" ] || { echo "No queue file at $QUEUE — nothing to do."; exit 0; }

# --- pick the next question: first in_progress (resume), else first pending ---
read -r QID QMODE QUESTION < <(python3 - "$QUEUE" <<'PY'
import sys, json
items = []
for line in open(sys.argv[1], encoding="utf-8"):
    line = line.strip()
    if not line: continue
    try: items.append(json.loads(line))
    except Exception: pass
pick = next((q for q in items if q.get("status") == "in_progress"), None) \
    or next((q for q in items if q.get("status") == "pending"), None)
if pick:
    mode = (pick.get("mode") or "research").strip() or "research"
    print(pick["id"], mode, pick["question"].replace("\n", " "))
PY
) || true   # read returns 1 on empty queue (EOF); set -e must not kill us here

if [ -z "${QID:-}" ]; then
  echo "No pending questions. Done."
  exit 0
fi
echo "Picked [$QID] (mode=$QMODE): $QUESTION"

# Mode selects the prompt template and the required-section sanity marker.
case "$QMODE" in
  trends)
    PROMPT_TEMPLATE="$PROMPTS_DIR/trends_prompt.txt"; SANITY_MARKER="Product Application" ;;
  *)
    PROMPT_TEMPLATE="$PROMPTS_DIR/deepdive_prompt.txt"; SANITY_MARKER="Trigger Hooks" ;;
esac
[ -f "$PROMPT_TEMPLATE" ] || { echo "FAIL: prompt template missing: $PROMPT_TEMPLATE"; exit 2; }

if [ "${1:-}" = "--dry-run" ]; then
  echo "(dry-run) would research (mode=$QMODE, template=$(basename "$PROMPT_TEMPLATE")) and write a report. Stopping."
  exit 0
fi

# slug: date + first ~6 words of question
SLUG="$TODAY-$(python3 - "$QUESTION" <<'PY'
import sys, re
q = sys.argv[1].lower()
q = re.sub(r"[^a-z0-9\s-]", "", q)
words = q.split()[:6]
print("-".join(words) or "research")
PY
)"
REPORT_PATH="$REPORTS_DIR/$SLUG.md"
echo "  slug:    $SLUG"

# --- mark in_progress (idempotent rewrite) ---
mark_status() {  # $1=id $2=status [$3=report_slug]
  python3 - "$QUEUE" "$1" "$2" "${3:-}" <<'PY'
import sys, json
path, qid, status, slug = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
out = []
for line in open(path, encoding="utf-8"):
    line = line.strip()
    if not line: continue
    try: q = json.loads(line)
    except Exception: continue
    if q.get("id") == qid:
        q["status"] = status
        if slug: q["report_slug"] = slug
    out.append(q)
with open(path, "w", encoding="utf-8") as f:
    for q in out:
        f.write(json.dumps(q, ensure_ascii=False) + "\n")
PY
}
mark_status "$QID" in_progress

# --- failure accounting: 3 strikes -> failed (stops infinite retry blocking the queue) ---
MAX_RETRIES=3
bump_retry() {  # $1=id $2=reason
  python3 - "$QUEUE" "$1" "$2" "$MAX_RETRIES" <<'PY'
import sys, json
path, qid, reason, max_r = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
out = []
for line in open(path, encoding="utf-8"):
    line = line.strip()
    if not line: continue
    try: q = json.loads(line)
    except Exception: continue
    if q.get("id") == qid:
        q["retry_count"] = int(q.get("retry_count") or 0) + 1
        q["last_error"] = reason
        if q["retry_count"] >= max_r:
            q["status"] = "failed"
            print(f"marked FAILED after {q['retry_count']} attempts: {reason}")
        else:
            print(f"attempt {q['retry_count']}/{max_r} failed ({reason}); will retry")
    out.append(q)
with open(path, "w", encoding="utf-8") as f:
    for q in out:
        f.write(json.dumps(q, ensure_ascii=False) + "\n")
PY
}

# --- render prompt ---
# Memory of past work: titles of existing reports go into the prompt so a new
# question on adjacent territory surfaces what's NEW instead of re-discovering
# the same findings and sources.
PREVIOUS_REPORTS="$(grep -h '^# ' "$REPORTS_DIR"/*.md 2>/dev/null | sed 's/^# /- /' || true)"
[ -n "$PREVIOUS_REPORTS" ] || PREVIOUS_REPORTS="(none yet)"
RENDERED="$(mktemp)"
python3 - "$PROMPT_TEMPLATE" "$RENDERED" "$QUESTION" "$TODAY" "$SWIPE_DIR" "$PREVIOUS_REPORTS" <<'PY'
import sys, pathlib
tpl, out, question, today, swipe, previous = sys.argv[1:7]
text = pathlib.Path(tpl).read_text()
for k, v in {"{{QUESTION}}": question, "{{TODAY}}": today,
             "{{SWIPE_DIR}}": swipe, "{{PREVIOUS_REPORTS}}": previous}.items():
    text = text.replace(k, v)
pathlib.Path(out).write_text(text)
PY

# task-lessons RECALL: prepend this agent's own past lessons to the rendered prompt.
if [ -x "$TL_DIR/recall.sh" ]; then
  LESSONS="$("$TL_DIR/recall.sh" research-deepdive 5 2>/dev/null || true)"
  if [ -n "$LESSONS" ]; then
    TMP_R="$(mktemp)"; { printf '%s\n\n' "$LESSONS"; cat "$RENDERED"; } > "$TMP_R"; mv -f "$TMP_R" "$RENDERED"
    echo "primed with $(printf '%s\n' "$LESSONS" | grep -c '^- ') past lesson(s)"
  fi
fi

# Stale-scrape guard: the firecrawl skill caches scrapes in .firecrawl/ with no
# TTL of its own — purge entries older than 7 days so a changed competitor page
# or updated article gets re-fetched instead of reused forever.
find "$AGENT_DIR/.firecrawl" -name '*.json' -mtime +7 -delete 2>/dev/null || true

# --- run headless claude (web + file research, unattended) ---
# macOS lacks GNU `timeout`; use gtimeout if present, else run without a hard cap.
TIMEOUT_CMD=()
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_CMD=(timeout "$RESEARCH_TIMEOUT")
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_CMD=(gtimeout "$RESEARCH_TIMEOUT")
else
  echo "note: no timeout binary found; running without a hard time cap"
fi
# Keep raw output in logs/ so failures are inspectable (overwritten each run per slug).
RAW="$LOGDIR/_raw-$SLUG.md"
echo ">> claude -p ($RESEARCH_MODEL${TIMEOUT_CMD:+, timeout ${RESEARCH_TIMEOUT}s}) ..."
STARTED=1; RUN_START=$SECONDS   # from here on, the EXIT trap captures the outcome
if ! "${TIMEOUT_CMD[@]+"${TIMEOUT_CMD[@]}"}" claude -p \
      --model "$RESEARCH_MODEL" \
      --dangerously-skip-permissions \
      --output-format text < "$RENDERED" > "$RAW" 2>"$LOGDIR/_claude-$SLUG.err"; then
  if command -v hermes_fallback >/dev/null 2>&1 && \
     hermes_fallback "$RENDERED" "$RAW" "$LOGDIR/_claude-$SLUG.err"; then
    VIA=hermes
    echo ">> recovered via hermes."
  else
    echo "FAIL: claude errored or timed out, hermes fallback unavailable/failed (see _claude-$SLUG.err)."
    bump_retry "$QID" "claude errored or timed out"
    exit 3
  fi
fi

# --- guards: non-empty, strip preamble to first H1, sanity check ---
if [ ! -s "$RAW" ]; then
  echo "FAIL: empty output."
  bump_retry "$QID" "empty output"
  exit 3
fi
python3 - "$RAW" "$REPORT_PATH.tmp" <<'PY'
import sys, pathlib, re
text = pathlib.Path(sys.argv[1]).read_text()
i = text.find("\n# ")
if text.lstrip().startswith("# "): cleaned = text.lstrip()
elif i != -1: cleaned = text[i+1:]
else: cleaned = text
# Brand rule: no em/en dashes. Em dash -> comma; en dash -> hyphen (e.g. 2025-2026).
cleaned = cleaned.replace(" — ", ", ").replace("—", ", ")
cleaned = cleaned.replace("–", "-")
cleaned = re.sub(r",\s*,", ",", cleaned)   # collapse any double commas the swap created
pathlib.Path(sys.argv[2]).write_text(cleaned)
PY
if [ ! -s "$REPORT_PATH.tmp" ] || ! grep -qi "$SANITY_MARKER" "$REPORT_PATH.tmp"; then
  echo "FAIL: report empty or missing required sections."
  rm -f "$REPORT_PATH.tmp"
  bump_retry "$QID" "missing required sections ($SANITY_MARKER)"
  exit 4
fi
mv -f "$REPORT_PATH.tmp" "$REPORT_PATH"

# --- mark done + append a feed entry + update status ---
mark_status "$QID" done "$SLUG"

TITLE="$(grep -m1 '^# ' "$REPORT_PATH" | sed 's/^# //')"
NOW="$(date -u +%FT%TZ)"
python3 - "$FEED_DIR/$(date +%Y-%m).jsonl" "$SLUG" "$NOW" "$TITLE" <<'PY'
import sys, json
feed, slug, now, title = sys.argv[1:5]
item = {"id": f"report-{slug}", "date": now, "source": "deep-dive",
        "type": "report", "severity": "notable",
        "title": f"New report: {title}",
        "summary": "Deep-dive research report completed. Open it under Deep-dive reports.",
        "url": "", "thumbnail": ""}
with open(feed, "a", encoding="utf-8") as f:
    f.write(json.dumps(item, ensure_ascii=False) + "\n")
PY
python3 - "$STATE_DIR/status.json" "$NOW" <<'PY'
import sys, json, pathlib, os
path, now = sys.argv[1], sys.argv[2]
data = {}
if os.path.exists(path):
    try: data = json.loads(pathlib.Path(path).read_text())
    except Exception: data = {}
data["last_deepdive_run"] = now
data.setdefault("monitors_ok", True)
pathlib.Path(path).write_text(json.dumps(data, indent=2))
PY

echo "[$(date)] DONE: $REPORT_PATH ($(wc -l <"$REPORT_PATH") lines)"

# --- draft a wiki-update proposal from the fresh report (human-in-the-loop:
# ingest-research.sh only writes to output/wiki-drafts/, never the wiki) ---
if [ -f "$SCRIPT_DIR/ingest-research.sh" ]; then
  echo ">> drafting wiki proposal for $SLUG ..."
  bash "$SCRIPT_DIR/ingest-research.sh" "$SLUG" \
    || echo "warn: wiki proposal draft failed (the report itself is fine; rerun: bash ingest-research.sh $SLUG)"
fi
