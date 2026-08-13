#!/bin/bash
# Correction-capture: mine Tomas-corrections from Claude transcripts (box + Mac)
# and feed them as lessons into the task-lessons ledger, which the existing
# task-lessons synth (Tue 05:30) clusters into gated promotion proposals.
#
# Stages: pull Mac transcripts (best-effort) -> scan.py (regex candidates) ->
# claude -p judge (keep real corrections) -> task-lessons/capture.py per lesson.
# Judged candidates are drained from candidates.jsonl; a failed judge leaves
# them queued for the next run.
set -uo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$HOME/.bun/bin:$PATH"

DIR="$HOME/systems/correction-capture"
BATCH_CAP=120
LOG_DIR="$DIR/logs"
mkdir -p "$LOG_DIR"
TS="$(date +%Y-%m-%d_%H%M%S)"
exec >>"$LOG_DIR/run-$TS.log" 2>&1
echo "=== correction-capture $TS ==="
cd "$DIR" || exit 1
# shellcheck source=/dev/null
[ -f "$HOME/systems/lib/hermes_fallback.sh" ] && . "$HOME/systems/lib/hermes_fallback.sh"

bash pull_mac.sh
python3 scan.py || { echo "FAILED: scan.py"; exit 1; }

[ -s candidates.jsonl ] || { echo "No pending candidates."; exit 0; }
BATCH="$(mktemp)"; REST="$(mktemp)"
head -n "$BATCH_CAP" candidates.jsonl > "$BATCH"
tail -n +"$((BATCH_CAP + 1))" candidates.jsonl > "$REST"
echo ">> judging $(wc -l < "$BATCH" | tr -d ' ') candidate(s), $(wc -l < "$REST" | tr -d ' ') deferred"

PROMPT_TMP="$(mktemp)"
{ cat judge_prompt.md; echo; echo "=== CANDIDATES ==="; cat "$BATCH"; } > "$PROMPT_TMP"
OUT_TMP="$(mktemp)"; ok=0
if timeout 1800 /usr/local/bin/claude-max --print --model claude-sonnet-4-6 --output-format text < "$PROMPT_TMP" > "$OUT_TMP" 2>"$DIR/_claude.err" && [ -s "$OUT_TMP" ]; then
  ok=1
elif command -v hermes_fallback >/dev/null 2>&1 && hermes_fallback "$PROMPT_TMP" "$OUT_TMP" "$DIR/_claude.err"; then
  ok=1; echo ">> recovered via hermes"
fi
if [ "$ok" != 1 ]; then
  echo "FAILED: judge (claude + hermes); candidates left queued"
  rm -f "$BATCH" "$REST" "$PROMPT_TMP" "$OUT_TMP"; exit 1
fi

# Feed accepted lessons into the task-lessons ledger; drain the judged batch.
python3 - "$BATCH" "$OUT_TMP" <<'PY'
import json, subprocess, sys, os
batch_path, out_path = sys.argv[1], sys.argv[2]
batch = {}
for line in open(batch_path):
    try:
        c = json.loads(line); batch[c["id"]] = c
    except Exception:
        pass
accepted = 0
for line in open(out_path):
    line = line.strip()
    if not line:
        continue
    try:
        j = json.loads(line)
    except Exception:
        continue
    c = batch.get(j.get("candidate_id"))
    if not c or not j.get("lesson"):
        continue
    rec = {
        "skill": j.get("skill", "general"),
        "verdict": "failed",
        "summary": j.get("summary", "")[:300],
        "lesson": j["lesson"][:300],
        "how_to_apply": j.get("how_to_apply", "")[:300],
        "context": f"correction from {c['source']} session {c['project']} at {c['ts']}",
        "tags": j.get("tags", ["correction"]),
    }
    r = subprocess.run(
        ["python3", os.path.expanduser("~/systems/task-lessons/capture.py")],
        input=json.dumps(rec), text=True, capture_output=True)
    if r.returncode == 0:
        accepted += 1
    else:
        print(f"capture.py failed for {j.get('candidate_id')}: {r.stderr[:200]}")
# Mark the whole judged batch as seen (accepted or rejected, both are consumed).
state_path = os.path.expanduser("~/systems/correction-capture/state.json")
state = json.load(open(state_path))
seen = set(state.get("seen", []))
seen.update(batch.keys())
state["seen"] = sorted(seen)
tmp = state_path + ".tmp"
json.dump(state, open(tmp, "w")); os.replace(tmp, state_path)
print(f"judge: {accepted} lesson(s) captured from {len(batch)} candidate(s)")
PY

mv "$REST" candidates.jsonl
rm -f "$BATCH" "$PROMPT_TMP" "$OUT_TMP"
echo "=== done $TS ==="
