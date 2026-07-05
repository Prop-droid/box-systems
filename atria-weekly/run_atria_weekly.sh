#!/usr/bin/env bash
# Weekly Atria FOLLOWED-BRANDS competitor swipe pull + strategist NEW-ads diff.
#
# Staged by fable-window task 15 (2026-07-04). NOT enabled by default.
# Enable per README.md. Complementary to the DAILY research-monitor.service
# (which pulls a brand-FILTERED gut-health set via MONITOR_BRAND_IDS); this job
# pulls the full FOLLOWED roster (no brand args) once a week.
#
# Hard-won headless rules baked in (see memory project_system_maintenance_loops):
#   - claude prompt goes via STDIN; --allowed-tools is variadic and eats a
#     positional prompt.
#   - write to a local tmp, validate (non-empty + H1), retry up to 3x, then land.
#   - a deterministic python diff is the fallback if headless claude is capped
#     (a limit-hit run exits 1; that is transient, but the weekly diff must still
#     land), so the job never produces nothing.
set -euo pipefail

CT="${CT:-$HOME/brain}"
ATRIA_SCRIPT="${ATRIA_SCRIPT:-$CT/.claude/skills/atria/scripts/atria_swipe_pull.py}"
OUT_DIR="${ATRIA_OUT_DIR:-$CT/projects/2026-06/competitor-ads-scrape/atria}"
KEY_FILE="${ATRIA_KEY_FILE:-$HOME/.config/atria/key}"
LOG_DIR="${LOG_DIR:-$HOME/systems/atria-weekly/logs}"
CLAUDE_BIN="${CLAUDE_BIN:-/usr/local/bin/claude-max}"
MODEL="${MODEL:-claude-sonnet-4-6}"

DATE="$(date +%F)"
mkdir -p "$LOG_DIR" "$OUT_DIR"
LOG="$LOG_DIR/atria-weekly-$DATE.log"
exec >>"$LOG" 2>&1
echo "== atria-weekly $DATE =="

export ATRIA_OUT_DIR="$OUT_DIR" ATRIA_KEY_FILE="$KEY_FILE"

[ -f "$ATRIA_SCRIPT" ] || { echo "FAIL: atria script missing $ATRIA_SCRIPT"; exit 2; }
[ -f "$KEY_FILE" ]     || { echo "FAIL: atria key missing $KEY_FILE"; \
  echo "       refresh: ssh mac 'cat ~/.config/atria/key' -> box $KEY_FILE ; chmod 600"; exit 3; }

# 1) Deterministic followed-brands pull -> atria-swipe-<date>.jsonl (+ .md summary).
echo ">> atria followed pull ..."
if ! python3 "$ATRIA_SCRIPT"; then
  echo "FAIL: atria pull errored (dead auth? rate limit? see above). Aborting; state untouched."
  exit 4
fi

# 2) Newest + previous FOLLOWED (no-suffix, exact-date) snapshots. The daily
#    gr-ns job writes suffixed names (atria-swipe-<date>-gr-ns-plus10.jsonl) which
#    the ????-??-?? glob deliberately excludes.
mapfile -t SNAPS < <(ls -t "$OUT_DIR"/atria-swipe-????-??-??.jsonl 2>/dev/null || true)
NEW="${SNAPS[0]:-}"
PREV="${SNAPS[1]:-}"
[ -n "$NEW" ] || { echo "FAIL: no followed snapshot produced"; exit 5; }
echo "newest=$NEW"
echo "prev=${PREV:-<none - first followed snapshot in $OUT_DIR>}"

DIFF_OUT="$OUT_DIR/atria-weekly-diff-$DATE.md"
rm -f "$DIFF_OUT"

# 3) Strategist NEW-ads diff via headless claude (bounded, stdin prompt).
run_claude() {
  cd "$CT"
  "$CLAUDE_BIN" --print --model "$MODEL" --dangerously-skip-permissions \
    --allowed-tools "Read Write Bash" <<EOF
You are running headless in a weekly cron. Do exactly this, nothing else.

Compare two Atria competitor-ad swipe snapshots (JSONL, one ad-copy cluster per line):
  NEW  = $NEW
  PREV = ${PREV:-<none>}

A "new cluster" = a line in NEW whose ad id (field "id", else "platform_native_id")
is NOT present in PREV. If PREV is <none>, treat every NEW line as new and say so.

Write a concise strategist markdown report to: $DIFF_OUT
Structure:
  # Atria weekly swipe - NEW ads diff ($DATE)
  - one line: total clusters in NEW, brand count, and count of new clusters
  - "## New clusters per brand" table (Brand | New clusters), sorted desc
  - "## Winning-lane new ads" : up to 20 new ads where winning_lane is true,
    each: brand, format, variant_count, angles, and the hook (title, else first
    ~140 chars of body). Sort by variant_count desc (scaling signal).
  - "## Owned-language watch" : up to 10 new ads tagged body_function
    (competitors camping on poop/bloat/regularity/not-a-laxative territory).
Use Bash with python3 to read/parse the JSONL. Keep it tight. No em dashes.
Do not touch any other file. When the report is written, stop.
EOF
}

ok=0
for try in 1 2 3; do
  echo ">> claude strategist diff attempt $try ..."
  if run_claude && [ -s "$DIFF_OUT" ] && head -1 "$DIFF_OUT" | grep -q '^# '; then
    ok=1; break
  fi
  echo "   attempt $try failed (claude capped or bad output); retrying"
  sleep 5
done

# 4) Deterministic fallback so a diff always lands (headless claude is capped-share).
if [ "$ok" -ne 1 ]; then
  echo ">> claude unavailable after 3 tries; deterministic python fallback diff"
  python3 - "$NEW" "${PREV:-}" "$DIFF_OUT" "$DATE" <<'PY'
import json, sys
from collections import defaultdict
new_p, prev_p, out_p, date = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
def load(p):
    if not p: return []
    r=[]
    with open(p) as f:
        for ln in f:
            ln=ln.strip()
            if ln: r.append(json.loads(ln))
    return r
new=load(new_p); prev=load(prev_p)
pid=lambda a:a.get("id") or a.get("platform_native_id")
prev_ids={pid(a) for a in prev}
newads=[a for a in new if pid(a) not in prev_ids]
def hook(a):
    t=(a.get("title") or "").strip()
    if t: return t
    return (a.get("body") or "").strip().replace("\n"," ")[:140]
by=defaultdict(list)
for a in newads: by[a.get("brand_name","?")].append(a)
L=[f"# Atria weekly swipe - NEW ads diff ({date})","",
   f"{len(new)} clusters across {len({a.get('brand_name') for a in new})} brands; "
   f"**{len(newads)} new** vs previous followed snapshot"
   f"{' (none - first snapshot, all counted new)' if not prev else ''}.","",
   "## New clusters per brand","","| Brand | New clusters |","|---|---|"]
for b,ads in sorted(by.items(), key=lambda x:-len(x[1])):
    L.append(f"| {b} | {len(ads)} |")
L+=["","## Winning-lane new ads",
    "_offer / urgency / usp, sorted by variant_count (scaling signal)._",""]
wl=sorted([a for a in newads if a.get("winning_lane")], key=lambda a:-(a.get("variant_count") or 0))[:20]
for a in wl:
    L.append(f"- **{a.get('brand_name')}** [{a.get('format')} · {a.get('variant_count')}× · "
             f"{','.join(a.get('angles') or []) or 'untagged'}] {hook(a)}")
bf=[a for a in newads if "body_function" in (a.get("angles") or [])][:10]
if bf:
    L+=["","## Owned-language watch (body-function territory)",""]
    for a in bf:
        L.append(f"- **{a.get('brand_name')}** ({a.get('variant_count')}×): {hook(a)}")
open(out_p,"w").write("\n".join(L)+"\n")
print("fallback diff written:", out_p, "new=", len(newads))
PY
fi

echo ">> DONE: $NEW"
echo ">> diff: $DIFF_OUT"
echo "== atria-weekly $DATE complete =="
