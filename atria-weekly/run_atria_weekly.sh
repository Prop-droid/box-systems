#!/usr/bin/env bash
# Weekly Atria FOLLOWED-BRANDS competitor swipe pull + strategist NEW-ads diff.
#
# Staged by fable-window task 15 (2026-07-04), enabled 2026-07-05 (Mon 07:30).
# Complementary to the DAILY research-monitor.service (which pulls a
# brand-FILTERED gut-health set via MONITOR_BRAND_IDS); this job pulls the full
# FOLLOWED roster once a week.
#
# Source chain (2026-11-04): Atria API first. Since 2026-11-01 Atria answers
# 403/40302 ("plan does not include the API surface"), so on any Atria failure
# the pull falls back to the public Meta Ad Library rendered under Camoufox
# (research-agent/bin/adlib_pull.py) over followed-roster.txt - the brand set
# Atria had us following, refreshed from every successful Atria pull. The
# fallback writes the same no-suffix atria-swipe-<date>.jsonl, so steps 2-4 and
# every consumer are unchanged.
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
# Meta Ad Library fallback (same script + interpreter research-monitor uses).
ADLIB_SCRIPT="${ADLIB_SCRIPT:-$HOME/systems/research-agent/bin/adlib_pull.py}"
ADLIB_PY="${ADLIB_PY:-$HOME/.local/share/uv/tools/scrapling/bin/python}"
ROSTER="${ATRIA_ROSTER:-$HOME/systems/atria-weekly/followed-roster.txt}"

DATE="$(date +%F)"
mkdir -p "$LOG_DIR" "$OUT_DIR"
LOG="$LOG_DIR/atria-weekly-$DATE.log"
exec >>"$LOG" 2>&1
echo "== atria-weekly $DATE =="

export ATRIA_OUT_DIR="$OUT_DIR" ATRIA_KEY_FILE="$KEY_FILE"

[ -f "$ATRIA_SCRIPT" ] || { echo "FAIL: atria script missing $ATRIA_SCRIPT"; exit 2; }
[ -f "$KEY_FILE" ]     || { echo "FAIL: atria key missing $KEY_FILE"; \
  echo "       refresh: ssh mac 'cat ~/.config/atria/key' -> box $KEY_FILE ; chmod 600"; exit 3; }

# 1) Followed-brands pull -> atria-swipe-<date>.jsonl (+ .md summary).
#    Atria first; on failure, Meta Ad Library over the roster. Either way the
#    file name is the no-suffix exact-date one that step 2 globs for.
SOURCE=""
echo ">> atria followed pull ..."
if python3 "$ATRIA_SCRIPT"; then
  SOURCE=atria
  # Atria's roster is authoritative: refresh the fallback roster from this pull.
  python3 - "$OUT_DIR/atria-swipe-$DATE.jsonl" "$ROSTER" <<'PY' || echo "warn: roster refresh failed (non-fatal)"
import json, re, sys
snap, out = sys.argv[1], sys.argv[2]
seen = {}
for ln in open(snap):
    if not ln.strip(): continue
    r = json.loads(ln)
    b = r.get("brand_id") or ""
    if re.fullmatch(r"m\d+", b) and b not in seen: seen[b] = (r.get("brand_name") or "").strip()
if len(seen) < 5: sys.exit(f"roster refresh skipped: only {len(seen)} brands in {snap}")
head = [l for l in open(out) if l.startswith("#")] if __import__("os").path.exists(out) else []
body = [f"{b}  {n}" for b, n in sorted(seen.items(), key=lambda x: x[1].lower())]
open(out, "w").write("".join(head) + ("\n" if head else "") + "\n".join(body) + "\n")
print(f"roster refreshed from Atria: {len(seen)} brands -> {out}")
PY
else
  echo "atria pull errored (plan-gated 403/40302 since 2026-11-01, dead auth, or rate limit - see above)."
  mapfile -t IDS < <(grep -oE '^m[0-9]+' "$ROSTER" 2>/dev/null || true)
  echo ">> fallback: Meta Ad Library pull via Camoufox over ${#IDS[@]} followed brands ($ROSTER) ..."
  [ -x "$ADLIB_PY" ]     || { echo "FAIL: $ADLIB_PY missing (scrapling uv tool env). Aborting; state untouched."; exit 4; }
  [ -f "$ADLIB_SCRIPT" ] || { echo "FAIL: $ADLIB_SCRIPT missing. Aborting; state untouched."; exit 4; }
  [ "${#IDS[@]}" -gt 0 ] || { echo "FAIL: empty roster $ROSTER. Aborting; state untouched."; exit 4; }
  # ADLIB_SUFFIX="" = write the plain atria-swipe-<date>.jsonl, not -<slug>-plusN.
  if ADLIB_SUFFIX="" ATRIA_RUN_DATE="$DATE" "$ADLIB_PY" "$ADLIB_SCRIPT" "${IDS[@]}"; then
    SOURCE=meta-ad-library
  else
    echo "FAIL: Atria AND the Meta Ad Library fallback errored. Aborting; state untouched."
    exit 4
  fi
fi
echo "pull source: $SOURCE"

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
#    Key on the Meta ad id (platform_native_id): Atria and Meta Ad Library
#    snapshots share it, so a source switch does not flag every ad as new.
run_claude() {
  cd "$CT"
  "$CLAUDE_BIN" --print --model "$MODEL" --dangerously-skip-permissions \
    --allowed-tools "Read Write Bash" <<EOF
You are running headless in a weekly cron. Do exactly this, nothing else.

Compare two Atria competitor-ad swipe snapshots (JSONL, one ad-copy cluster per line):
  NEW  = $NEW   (source: $SOURCE)
  PREV = ${PREV:-<none>}

A "new cluster" = a line in NEW whose Meta ad id (field "platform_native_id",
else "id") is NOT present in PREV. If PREV is <none>, treat every NEW line as new and say so.

Write a concise strategist markdown report to: $DIFF_OUT
Structure:
  # Atria weekly swipe - NEW ads diff ($DATE)
  - one line: total clusters in NEW, brand count, count of new clusters, and the source ($SOURCE)
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
  python3 - "$NEW" "${PREV:-}" "$DIFF_OUT" "$DATE" "$SOURCE" <<'PY'
import json, sys
from collections import defaultdict
new_p, prev_p, out_p, date, source = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
def load(p):
    if not p: return []
    r=[]
    with open(p) as f:
        for ln in f:
            ln=ln.strip()
            if ln: r.append(json.loads(ln))
    return r
new=load(new_p); prev=load(prev_p)
pid=lambda a:a.get("platform_native_id") or a.get("id")
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
   f"{' (none - first snapshot, all counted new)' if not prev else ''}. Source: {source}.","",
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

echo ">> DONE: $NEW (source: $SOURCE)"
echo ">> diff: $DIFF_OUT"
echo "== atria-weekly $DATE complete =="
