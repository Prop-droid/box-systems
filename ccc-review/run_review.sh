#!/usr/bin/env bash
# ccc-review — weekly multi-agent review scan of one CCC surface slice (rotating).
# Read-only findings only (bugs, UX, coherence) — never edits code; fixes happen
# on Tomas's "proceed" in #dev. Born from the 2026-08-18 INTEL sweep that found
# ~50 real defects (5 silently-dead headline features) in surfaces marked "done".
# Rotation (ISO week mod 4): intel → performance → winners → platform.
# DRY_RUN=1 = review + print, no Discord post. SLICE=<name> forces a slice.
set -uo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

BASE="$HOME/systems/ccc-review"
REPORTS="$BASE/reports"
LOG="$BASE/review.log"
CCC="$HOME/creative-command-center"
NOTIFY="$HOME/systems/lib/discord-notify.sh"
MODEL="${MODEL:-claude-sonnet-4-6}"

mkdir -p "$REPORTS"
[ "${DRY_RUN:-0}" = "1" ] || exec >>"$LOG" 2>&1
echo "=== [$(date)] ccc-review run ==="

fail() {
  echo "FAIL: $1"
  "$NOTIFY" "CCC review failed" "ccc-review FAILED on box: $1 (see ~/systems/ccc-review/review.log)" high || true
  exit 1
}

SLICES=(intel performance winners platform)
SLICE="${SLICE:-${SLICES[$(( $(date +%V | sed 's/^0//') % 4 ))]}}"
TODAY=$(date +%F)
OUT="$REPORTS/$TODAY-$SLICE.md"
[ -s "$OUT" ] && { echo "Already reviewed today ($SLICE) — exiting"; exit 0; }

[ -f "$BASE/prompt_$SLICE.txt" ] || fail "unknown slice '$SLICE'"
command -v claude >/dev/null || fail "claude CLI not on PATH"
curl -sf --max-time 10 -o /dev/null "http://localhost:3000/" || fail "CCC not serving on :3000"

RAW="$REPORTS/_raw.md"
for attempt in 1 2; do
  cat "$BASE/prompt_common.txt" "$BASE/prompt_$SLICE.txt" \
    | ( cd "$CCC" && timeout 3000 /usr/local/bin/claude-max --print --model "$MODEL" \
        --dangerously-skip-permissions ) > "$RAW" || true
  # empty-result trap: a review with no TL;DR section is a failed run, not "no findings"
  [ -s "$RAW" ] && grep -q "^TL;DR" "$RAW" && break
  echo "attempt $attempt: invalid output, retrying"; sleep 60
done
grep -q "^TL;DR" "$RAW" || fail "claude produced no valid review after 2 attempts"

mv "$RAW" "$OUT"
echo "report: $OUT ($(wc -l <"$OUT") lines)"

if [ "${DRY_RUN:-0}" = "1" ]; then
  echo "--- DRY_RUN report ---"; cat "$OUT"; exit 0
fi

# TL;DR goes to #dev as the Developer bot — that is where Tomas replies and
# where the "<path> proceed" pattern dispatches the fix session. Full report
# stays on disk; #ops-log keeps failure alerts only.
TLDR=$(awk '/^TL;DR/{f=1} f{print} f && NF==0 && NR>1 && ++blank>=1{exit}' "$OUT" | head -c 1500)
{ echo "🔎 **CCC review · $SLICE · $TODAY**"
  echo "$TLDR"
  echo
  echo "Reply \`~/systems/ccc-review/reports/$TODAY-$SLICE.md proceed\` to implement."
} | bash "$HOME/systems/lib/discord-post.sh" 1531564369672929290 DEV_TOKEN \
  || "$NOTIFY" "CCC review · $SLICE · $TODAY (dev post failed)" "$TLDR" default || true
echo "posted to Discord"
