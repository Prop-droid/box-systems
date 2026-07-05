#!/usr/bin/env bash
# iteration-suggestions — twice-weekly creative iteration drop into Tomas Pod (ClickUp chat)
# Reads the latest sha-weekly-report raw data, drafts suggestions via claude -p,
# resolves {{SH-XXXXX}} refs to task links via ClickUp REST, posts via chat API v3.
# Scheduled Tue+Thu via iteration-suggestions.timer; self-disables after END_DATE.
set -uo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

BASE="$HOME/systems/iteration-suggestions"
DROPS="$BASE/drops"
LOG="$BASE/run.log"
CHANNEL_ID="8cj5bz5-125371"          # Tomas Pod
WORKSPACE_ID="9011638245"
END_DATE="2026-07-17"                # last scheduled drop is Thu 2026-07-16
NTFY_TOPIC="tomas-tab-958e4431"

mkdir -p "$DROPS"
exec >>"$LOG" 2>&1
echo "=== [$(date)] iteration-suggestions run ==="

fail() {
  echo "FAIL: $1"
  curl -s -d "iteration-suggestions FAILED on box: $1 (see ~/systems/iteration-suggestions/run.log)" \
    -H "Title: Iteration drop failed" "https://ntfy.sh/$NTFY_TOPIC" >/dev/null || true
  exit 1
}

TODAY=$(date +%F)
if [[ "$TODAY" > "$END_DATE" ]]; then
  echo "Past end date $END_DATE — disabling timer"
  systemctl --user disable --now iteration-suggestions.timer 2>/dev/null || true
  exit 0
fi

if [[ -s "$DROPS/$TODAY.md" ]]; then
  echo "Already dropped today — exiting"
  exit 0
fi

command -v claude >/dev/null || fail "claude CLI not on PATH"

TOK=$(grep -rhoE 'pk_[0-9]+_[A-Z0-9]{24,}' ~/.hermes ~/.config ~/systems 2>/dev/null | sort -u | head -1)
[[ -n "$TOK" ]] || fail "ClickUp pk_ token not found on disk"

# ---- Latest weekly-report run dir (folder name = week-start Monday) ----
RDIR=""
for d in "$HOME"/brain/projects/*/sha-weekly-report/20*/; do
  [[ -s "${d}report.md" ]] || continue
  b=$(basename "$d")
  if [[ -z "$RDIR" || "$b" > "$(basename "$RDIR")" ]]; then RDIR="${d%/}"; fi
done
[[ -n "$RDIR" ]] || fail "no weekly report run found under ~/brain/projects"
WEEK_START=$(basename "$RDIR")
WEEK_END=$(date -d "$WEEK_START +6 days" +%F)
echo "Data: $RDIR (week $WEEK_START to $WEEK_END)"

# ---- Assemble prompt ----
PROMPT="$BASE/_assembled_prompt.txt"
{
  cat "$BASE/prompt_template.txt"
  echo
  echo "## Report data week: $WEEK_START to $WEEK_END (label the drop with this week)"
  echo "## Today: $TODAY"
  for f in 03_top_spend 04_top_roas 05_losers 10_hook_hold 11_fatigue 12_concepts; do
    [[ -s "$RDIR/$f.txt" ]] || continue
    echo
    echo "### DATA: $f"
    cat "$RDIR/$f.txt"
  done
  echo
  echo "### PREVIOUS DROPS (do not repeat task + iteration-type combos):"
  prev=$(ls -t "$DROPS"/*.md 2>/dev/null | head -3)
  if [[ -n "$prev" ]]; then
    for f in $prev; do echo "--- $(basename "$f")"; cat "$f"; done
  else
    echo "(none)"
  fi
} > "$PROMPT"

# ---- Generate (retry x3) ----
RAW="$BASE/_raw.md"
ok=0
for attempt in 1 2 3; do
  if claude -p --model claude-sonnet-4-6 --output-format text < "$PROMPT" > "$RAW" 2>"$BASE/_claude.err"; then
    if grep -q "Iteration Suggestions" "$RAW" && grep -q "{{SH-" "$RAW"; then ok=1; break; fi
    echo "WARN: attempt $attempt — output missing required markers, retrying"
  else
    echo "WARN: attempt $attempt — claude CLI errored, retrying"
  fi
  sleep 10
done
[[ $ok -eq 1 ]] || fail "claude output invalid after 3 attempts"

# ---- Resolve {{SH-XXXXX}} -> task links, then post ----
FINAL="$BASE/_final.md"
CLICKUP_TOKEN="$TOK" RAW_FILE="$RAW" FINAL_FILE="$FINAL" \
WORKSPACE_ID="$WORKSPACE_ID" CHANNEL_ID="$CHANNEL_ID" DRY_RUN="${DRY_RUN:-0}" \
python3 - <<'PY' || fail "link resolution / post step errored"
import json, os, re, sys, urllib.request

tok = os.environ["CLICKUP_TOKEN"]
ws, ch = os.environ["WORKSPACE_ID"], os.environ["CHANNEL_ID"]
text = open(os.environ["RAW_FILE"]).read().strip()
# strip any preamble before the drop header
i = text.find("🔁")
if i > 0:
    text = text[i:]

def api(url, data=None, method="GET"):
    req = urllib.request.Request(url, data=data, method=method,
        headers={"Authorization": tok, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, json.loads(r.read().decode() or "{}")

refs = sorted(set(re.findall(r"\{\{(SH-\d+)\}\}", text)))
unresolved = []
for ref in refs:
    try:
        st, d = api(f"https://api.clickup.com/api/v2/task/{ref}?custom_task_ids=true&team_id={ws}")
        url = d.get("url") or f"https://app.clickup.com/t/{d['id']}"
        text = text.replace("{{%s}}" % ref, f"[{ref}]({url})")
    except Exception as e:
        unresolved.append(ref)
        text = text.replace("{{%s}}" % ref, ref)
if unresolved:
    print(f"WARN: unresolved refs: {unresolved}", file=sys.stderr)

open(os.environ["FINAL_FILE"], "w").write(text)

if os.environ.get("DRY_RUN") == "1":
    print("DRY_RUN=1 — not posting")
    sys.exit(0)

body = json.dumps({"type": "message", "content_format": "text/md", "content": text}).encode()
st, d = api(f"https://api.clickup.com/api/v3/workspaces/{ws}/chat/channels/{ch}/messages", body, "POST")
if st not in (200, 201):
    print(f"post failed: HTTP {st}", file=sys.stderr); sys.exit(1)
print(f"posted message id={d.get('data', {}).get('id') or d.get('id')}")
PY

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  echo "[$(date)] DRY RUN done: $FINAL"
  exit 0
fi

cp "$FINAL" "$DROPS/$TODAY.md"
echo "[$(date)] DONE: posted + saved $DROPS/$TODAY.md"
