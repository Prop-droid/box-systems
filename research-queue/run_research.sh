#!/bin/bash
# research-queue — upgraded research pipeline runner (v1, staged 2026-07-12).
#
# One question in -> one adversarially-verified, cited report out.
# Stages (each resumable; deterministic script owns fan-out/retry/validation,
# LLM calls do ONLY judgment — fable-window lesson 6):
#   S1 scope       decompose question into search angles        (haiku)
#   S2 sweeps      DUAL-RUN: web lane (headless claude) + perplexity lane
#                  (hermes -z, which owns the perplexity MCP) in parallel
#   S3 merge       deterministic claim extraction + dedup       (no LLM)
#   S4 verify      adversarial refutation pass over claims      (sonnet)
#   S5 synthesize  cited report from sweeps + verdicts          (sonnet)
#   S6 gate        deterministic eval-gate (gate.py hard kills) (no LLM)
#   S7 file        gbrain draft page (writes to gbrain only if RQ_GBRAIN_FILE=1)
#
# Usage:
#   bash run_research.sh --question "..." [--slug my-slug] [--fast]
#   bash run_research.sh --queue [--fast]     # drain next pending from queue/questions.jsonl
#   bash run_research.sh --dry-run --question "..."
#
# Resumable: rerun with the same slug and completed stages are skipped
# (size>0 + validated outputs). A usage-window pause mid-run exits 0 with
# stage files intact; the next invocation continues where it stopped.
set -euo pipefail
export RTK_HOOK_OFF=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS="$SCRIPT_DIR/prompts"
export PATH="$HOME/.local/bin:$HOME/.bun/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# ---- model routing (env-overridable; sonnet-tier for cron discipline) -------
RQ_SCOPE_MODEL="${RQ_SCOPE_MODEL:-claude-haiku-4-5}"
RQ_SWEEP_MODEL="${RQ_SWEEP_MODEL:-claude-sonnet-4-6}"
RQ_VERIFY_MODEL="${RQ_VERIFY_MODEL:-claude-sonnet-4-6}"
RQ_SYNTH_MODEL="${RQ_SYNTH_MODEL:-claude-sonnet-4-6}"

# ---- cost bounds ------------------------------------------------------------
RQ_ANGLES="${RQ_ANGLES:-5}"            # search angles from scope stage
RQ_MAX_CLAIMS="${RQ_MAX_CLAIMS:-12}"   # hard cap on claims sent to verify
RQ_MIN_SOURCES="${RQ_MIN_SOURCES:-5}"  # gate: min distinct source domains
T_SCOPE="${T_SCOPE:-300}"; T_SWEEP="${T_SWEEP:-900}"
T_VERIFY="${T_VERIFY:-700}"; T_SYNTH="${T_SYNTH:-600}"
RQ_INLINE_CAP="${RQ_INLINE_CAP:-24000}"  # chars of each sweep inlined into synth prompt

QUESTION=""; SLUG=""; QMODE=""; QID=""; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --question) QUESTION="$2"; shift 2 ;;
    --slug)     SLUG="$2"; shift 2 ;;
    --queue)    QMODE=queue; shift ;;
    --fast)     RQ_ANGLES=3; RQ_MAX_CLAIMS=8; RQ_MIN_SOURCES=3
                T_SCOPE=240; T_SWEEP=540; T_VERIFY=480; T_SYNTH=420; shift ;;
    --dry-run)  DRY=1; shift ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done

PAUSE_FLAG="$HOME/.claude/PAUSE_CLAUDE_BG"
if [ -f "$PAUSE_FLAG" ]; then echo "paused (usage-guard flag present); exiting 0, rerun later."; exit 0; fi
command -v claude >/dev/null || { echo "FAIL: claude CLI not on PATH"; exit 2; }
CLAUDE_BIN="/usr/local/bin/claude-max"; [ -x "$CLAUDE_BIN" ] || CLAUDE_BIN="claude"

# ---- queue drain mode --------------------------------------------------------
QUEUE_FILE="$SCRIPT_DIR/queue/questions.jsonl"
if [ "$QMODE" = queue ]; then
  read -r QID QUESTION < <(python3 - "$QUEUE_FILE" <<'PY'
import sys, json, os
path = sys.argv[1]
if not os.path.exists(path): sys.exit(0)
items = [json.loads(l) for l in open(path) if l.strip()]
pick = next((q for q in items if q.get("status") == "in_progress"), None) \
    or next((q for q in items if q.get("status") == "pending"), None)
if pick: print(pick["id"], pick["question"].replace("\n", " "))
PY
  ) || true
  [ -n "${QID:-}" ] || { echo "queue empty, nothing pending."; exit 0; }
fi
[ -n "$QUESTION" ] || { echo "FAIL: no question (use --question or --queue)"; exit 2; }

TODAY="$(date +%F)"
[ -n "$SLUG" ] || SLUG="$TODAY-$(python3 -c "
import sys, re; q = re.sub(r'[^a-z0-9\s-]', '', sys.argv[1].lower())
print('-'.join(q.split()[:6]) or 'research')" "$QUESTION")"
WORK="$SCRIPT_DIR/out/$SLUG"; LOGD="$SCRIPT_DIR/logs/$SLUG"
mkdir -p "$WORK" "$LOGD"
META="$WORK/meta.json"

mark_queue() {  # $1=status  (no-op outside queue mode)
  [ -n "${QID:-}" ] || return 0
  python3 - "$QUEUE_FILE" "$QID" "$1" "$SLUG" <<'PY'
import sys, json
path, qid, status, slug = sys.argv[1:5]
out = []
for line in open(path):
    if not line.strip(): continue
    q = json.loads(line)
    if q.get("id") == qid: q["status"] = status; q["report_slug"] = slug
    out.append(q)
open(path, "w").write("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in out))
PY
}

meta_set() {  # $1=key $2=value (string)
  python3 - "$META" "$1" "$2" <<'PY'
import sys, json, os
path, k, v = sys.argv[1:4]
d = json.load(open(path)) if os.path.exists(path) else {}
d[k] = v
json.dump(d, open(path, "w"), indent=2)
PY
}

echo "=================================================="
echo "[$(date)] research-queue run"
echo "  slug:     $SLUG"
echo "  question: $QUESTION"
echo "  models:   scope=$RQ_SCOPE_MODEL sweep=$RQ_SWEEP_MODEL verify=$RQ_VERIFY_MODEL synth=$RQ_SYNTH_MODEL"
echo "  bounds:   angles=$RQ_ANGLES claims<=$RQ_MAX_CLAIMS min_domains=$RQ_MIN_SOURCES"
echo "=================================================="
[ "$DRY" = 1 ] && { echo "(dry-run) would run stages S1-S7 into $WORK. Stopping."; exit 0; }
meta_set question "$QUESTION"; meta_set date "$TODAY"
mark_queue in_progress

render() {  # $1=template $2=out; substitutes {{QUESTION}} {{TODAY}} {{ANGLES_N}} {{ANGLES}} {{CLAIMS}} {{EXTRA}}
  python3 - "$1" "$2" "$QUESTION" "$TODAY" "$RQ_ANGLES" "${ANGLES_TXT:-}" "${CLAIMS_TXT:-}" "${EXTRA_TXT:-}" <<'PY'
import sys, pathlib
tpl, out, question, today, n, angles, claims, extra = sys.argv[1:9]
t = pathlib.Path(tpl).read_text()
for k, v in {"{{QUESTION}}": question, "{{TODAY}}": today, "{{ANGLES_N}}": n,
             "{{ANGLES}}": angles, "{{CLAIMS}}": claims, "{{EXTRA}}": extra}.items():
    t = t.replace(k, v)
pathlib.Path(out).write_text(t)
PY
}

run_claude() {  # $1=model $2=timeout $3=prompt_file $4=out $5=tools $6=label; 2 attempts
  local attempt rc
  for attempt in 1 2; do
    echo ">> claude [$6] $1 (attempt $attempt, ${2}s cap)"
    rc=0
    timeout "$2" "$CLAUDE_BIN" --print --model "$1" --dangerously-skip-permissions \
      --allowed-tools "$5" < "$3" > "$4.tmp" 2>>"$LOGD/$6.err" || rc=$?
    if [ -f "$PAUSE_FLAG" ]; then echo "paused mid-run; exiting 0."; rm -f "$4.tmp"; exit 0; fi
    if [ $rc -eq 0 ] && [ -s "$4.tmp" ]; then mv -f "$4.tmp" "$4"; return 0; fi
    echo "   attempt $attempt failed (rc=$rc, size=$(wc -c <"$4.tmp" 2>/dev/null || echo 0))"
  done
  rm -f "$4.tmp"; return 1
}

# ---- S1: scope — question -> angles.json ------------------------------------
ANGLES_JSON="$WORK/01-angles.json"
if [ ! -s "$ANGLES_JSON" ]; then
  render "$PROMPTS/scope.txt" "$WORK/_p1.txt"
  run_claude "$RQ_SCOPE_MODEL" "$T_SCOPE" "$WORK/_p1.txt" "$WORK/_s1.raw" "" s1-scope \
    || { echo "FAIL: scope stage"; mark_queue failed; exit 3; }
  python3 - "$WORK/_s1.raw" "$ANGLES_JSON" "$RQ_ANGLES" <<'PY' || { echo "FAIL: scope output invalid"; exit 3; }
import sys, json, re
raw = open(sys.argv[1]).read()
m = re.search(r"\[.*\]", raw, re.S)
angles = json.loads(m.group(0)) if m else []
angles = [str(a).strip() for a in angles if str(a).strip()][: int(sys.argv[3])]
assert len(angles) >= 2, f"only {len(angles)} angles parsed"
json.dump(angles, open(sys.argv[2], "w"), indent=2)
PY
fi
ANGLES_TXT="$(python3 -c "import json,sys; print('\n'.join('- '+a for a in json.load(open(sys.argv[1]))))" "$ANGLES_JSON")"
echo "S1 angles:"; echo "$ANGLES_TXT"

# ---- S2: dual sweeps (parallel; both lanes end synchronously via wait) ------
SWEEP_WEB="$WORK/02-sweep-web.md"; SWEEP_PPLX="$WORK/02-sweep-pplx.md"
if [ ! -s "$SWEEP_WEB" ]; then
  render "$PROMPTS/sweep_web.txt" "$WORK/_p2w.txt"
fi
if [ ! -s "$SWEEP_PPLX" ]; then
  render "$PROMPTS/sweep_pplx.txt" "$WORK/_p2p.txt"
fi
WEB_PID=""; PPLX_PID=""
if [ ! -s "$SWEEP_WEB" ]; then
  run_claude "$RQ_SWEEP_MODEL" "$T_SWEEP" "$WORK/_p2w.txt" "$SWEEP_WEB" \
    "WebSearch WebFetch Bash Read Grep Glob" s2-web &
  WEB_PID=$!
fi
if [ ! -s "$SWEEP_PPLX" ]; then
  if command -v hermes >/dev/null 2>&1; then
    ( timeout "$T_SWEEP" hermes -z "$(cat "$WORK/_p2p.txt")" --yolo \
        > "$SWEEP_PPLX.tmp" 2>>"$LOGD/s2-pplx.err" && [ -s "$SWEEP_PPLX.tmp" ] \
        && mv -f "$SWEEP_PPLX.tmp" "$SWEEP_PPLX" ) &
    PPLX_PID=$!
  fi
fi
[ -n "$WEB_PID" ] && { wait "$WEB_PID" || true; }
[ -n "$PPLX_PID" ] && { wait "$PPLX_PID" || true; }
[ -f "$PAUSE_FLAG" ] && { echo "paused mid-run; exiting 0."; exit 0; }
[ -s "$SWEEP_WEB" ] || { echo "FAIL: web sweep produced nothing"; mark_queue failed; exit 3; }

# Perplexity-lane degrade: hermes missing or failed -> run a SECOND independent
# claude web sweep with the contrarian framing so the run is still dual-sweep.
# The report must carry a DEGRADED note (gate enforces it). Worse report > silence.
if [ ! -s "$SWEEP_PPLX" ]; then
  echo "WARN: perplexity lane (hermes) unavailable/failed — degrading to 2nd independent web sweep."
  meta_set degraded "perplexity lane unavailable; second independent web sweep used instead"
  EXTRA_TXT="NOTE: the Perplexity backend is unavailable. You are the independent SECOND sweep. Deliberately use different search phrasings and different source types than an obvious first pass would."
  render "$PROMPTS/sweep_pplx.txt" "$WORK/_p2p.txt"; EXTRA_TXT=""
  run_claude "$RQ_SWEEP_MODEL" "$T_SWEEP" "$WORK/_p2p.txt" "$SWEEP_PPLX" \
    "WebSearch WebFetch Bash Read Grep Glob" s2-pplx-degraded \
    || { echo "WARN: second sweep also failed; continuing single-lane."; meta_set degraded "single-lane run: only one sweep succeeded"; }
fi
echo "S2 sweeps: web=$(wc -c <"$SWEEP_WEB")B pplx=$( [ -s "$SWEEP_PPLX" ] && wc -c <"$SWEEP_PPLX" || echo 0)B"

# ---- S3: deterministic claim merge ------------------------------------------
CLAIMS="$WORK/03-claims.jsonl"
if [ ! -s "$CLAIMS" ]; then
  python3 - "$SWEEP_WEB" "$SWEEP_PPLX" "$CLAIMS" "$RQ_MAX_CLAIMS" "$META" <<'PY'
import sys, json, re, os
web, pplx, out, cap, meta_p = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]

def extract(path, backend):
    if not os.path.exists(path): return []
    text = open(path, errors="replace").read()
    m = re.search(r"===CLAIMS===(.*?)===END CLAIMS===", text, re.S)
    if not m: return []
    rows = []
    for line in m.group(1).splitlines():
        line = line.strip().strip("`")
        if not line.startswith("{"): continue
        try:
            d = json.loads(line)
            if d.get("claim"): rows.append({"claim": str(d["claim"]), "urls": [u for u in [d.get("url", "")] if u], "backends": [backend]})
        except Exception: pass
    return rows

def toks(s): return set(re.findall(r"[a-z0-9]+", s.lower())) - {"the","a","an","of","in","for","to","and","is","are"}

merged = []
for row in extract(web, "web") + extract(pplx, "perplexity"):
    for m2 in merged:
        t1, t2 = toks(row["claim"]), toks(m2["claim"])
        if t1 and t2 and len(t1 & t2) / len(t1 | t2) >= 0.6:
            m2["urls"] = sorted(set(m2["urls"] + row["urls"]))
            m2["backends"] = sorted(set(m2["backends"] + row["backends"]))
            break
    else:
        merged.append(row)

# cross-backend claims first (highest value: agreement or contradiction);
# single-backend remainder INTERLEAVED web/pplx so the cap never starves one
# lane (smoke run 2026-07-12 exposed exactly that failure)
cross = [r for r in merged if len(r["backends"]) > 1]
singles = {b: [r for r in merged if r["backends"] == [b]] for b in ("web", "perplexity")}
inter = []
while singles["web"] or singles["perplexity"]:
    for b in ("web", "perplexity"):
        if singles[b]: inter.append(singles[b].pop(0))
total = len(merged)
merged = (cross + inter)[:cap]
dropped = total - len(merged)
for i, r in enumerate(merged): r["id"] = f"C{i+1}"
open(out, "w").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in merged))
meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {}
meta["claims_total"], meta["claims_dropped_by_cap"] = len(merged), dropped
json.dump(meta, open(meta_p, "w"), indent=2)
print(f"S3: {len(merged)} claims kept, {dropped} dropped by cap (no silent caps: noted in meta)")
PY
fi
N_CLAIMS=$(wc -l <"$CLAIMS")
[ "$N_CLAIMS" -ge 1 ] || { echo "FAIL: no falsifiable claims extracted from either sweep"; mark_queue failed; exit 4; }

# ---- S4: adversarial verify ---------------------------------------------------
VERDICTS="$WORK/04-verdicts.jsonl"
if [ ! -s "$VERDICTS" ]; then
  CLAIMS_TXT="$(python3 -c "
import json,sys
rows=[json.loads(l) for l in open(sys.argv[1])]
print('\n'.join(f\"{r['id']}. {r['claim']}  [seen by: {','.join(r['backends'])}] [urls: {' '.join(r['urls'][:3]) or 'none'}]\" for r in rows))" "$CLAIMS")"
  render "$PROMPTS/verify.txt" "$WORK/_p4.txt"; CLAIMS_TXT=""
  run_claude "$RQ_VERIFY_MODEL" "$T_VERIFY" "$WORK/_p4.txt" "$WORK/_s4.raw" \
    "WebSearch WebFetch Bash Read Grep Glob" s4-verify \
    || { echo "WARN: verify stage failed; all claims degrade to UNVERIFIED."; : > "$WORK/_s4.raw"; }
  python3 - "$WORK/_s4.raw" "$CLAIMS" "$VERDICTS" <<'PY'
import sys, json, re
raw = open(sys.argv[1], errors="replace").read() if sys.argv[1] else ""
claims = [json.loads(l) for l in open(sys.argv[2])]
got = {}
m = re.search(r"===VERDICTS===(.*?)===END VERDICTS===", raw, re.S)
for line in (m.group(1).splitlines() if m else []):
    line = line.strip().strip("`")
    if not line.startswith("{"): continue
    try:
        d = json.loads(line)
        if d.get("id") and d.get("verdict") in ("CONFIRMED", "UNVERIFIED", "REFUTED"): got[d["id"]] = d
    except Exception: pass
out = []
for c in claims:
    v = got.get(c["id"], {"id": c["id"], "verdict": "UNVERIFIED", "note": "no verdict returned; deterministic degrade"})
    v["claim"] = c["claim"]; v.setdefault("evidence_urls", [])
    out.append(v)
open(sys.argv[3], "w").write("".join(json.dumps(v, ensure_ascii=False) + "\n" for v in out))
from collections import Counter
print("S4 verdicts:", dict(Counter(v["verdict"] for v in out)))
PY
fi

# ---- S5: synthesize -----------------------------------------------------------
DRAFT="$WORK/05-report.draft.md"; REPORT="$WORK/report.md"
synth() {  # $1=gate_feedback ("" on first pass)
  python3 - "$SWEEP_WEB" "$SWEEP_PPLX" "$VERDICTS" "$META" "$WORK/_inputs.txt" "$RQ_INLINE_CAP" <<'PY'
import sys, json, os
web, pplx, verd, meta_p, out, cap = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], int(sys.argv[6])
def clip(p):
    if not os.path.exists(p): return "(lane unavailable)"
    t = open(p, errors="replace").read()
    return t[:cap] + ("\n[...truncated deterministically at cap...]" if len(t) > cap else "")
meta = json.load(open(meta_p))
parts = ["## SWEEP A (web lane)\n" + clip(web), "## SWEEP B (perplexity lane)\n" + clip(pplx),
         "## VERDICTS (adversarial verification, authoritative)\n" + open(verd).read()]
if meta.get("degraded"): parts.append("## DEGRADATION NOTE (must appear in report)\nDEGRADED: " + meta["degraded"])
if meta.get("claims_dropped_by_cap"): parts.append(f"## CAP NOTE\n{meta['claims_dropped_by_cap']} extracted claims were dropped by the verification cap; note this under Open questions.")
open(out, "w").write("\n\n".join(parts))
PY
  EXTRA_TXT="$(cat "$WORK/_inputs.txt")
${1:+GATE FEEDBACK FROM THE PREVIOUS ATTEMPT (fix every item): $1}"
  render "$PROMPTS/synthesize.txt" "$WORK/_p5.txt"; EXTRA_TXT=""
  run_claude "$RQ_SYNTH_MODEL" "$T_SYNTH" "$WORK/_p5.txt" "$DRAFT" "" s5-synth
}
if [ ! -s "$REPORT" ]; then
  [ -s "$DRAFT" ] || synth "" || { echo "FAIL: synthesis"; mark_queue failed; exit 5; }

  # ---- S6: deterministic eval-gate; one feedback retry, then land with banner ---
  GATE_OUT="$WORK/gate.result"
  if python3 "$SCRIPT_DIR/gate.py" "$DRAFT" "$VERDICTS" "$META" "$RQ_MIN_SOURCES" > "$GATE_OUT" 2>&1; then
    echo "S6 gate: PASS"
  else
    echo "S6 gate: FAIL — one synthesis retry with gate feedback"; cat "$GATE_OUT"
    synth "$(cat "$GATE_OUT")" || true
    if python3 "$SCRIPT_DIR/gate.py" "$DRAFT" "$VERDICTS" "$META" "$RQ_MIN_SOURCES" > "$GATE_OUT" 2>&1; then
      echo "S6 gate: PASS (after retry)"
    else
      echo "S6 gate: still FAILING — landing report with FAILED-GATE banner (worse report > silence)"
      { echo "> GATE: FAILED — $(tr '\n' '; ' <"$GATE_OUT")"; echo; cat "$DRAFT"; } > "$DRAFT.tmp" && mv "$DRAFT.tmp" "$DRAFT"
      meta_set gate "FAILED"
    fi
  fi
  # strip any pre-H1 preamble, land atomically
  python3 - "$DRAFT" "$REPORT" <<'PY'
import sys, pathlib
t = pathlib.Path(sys.argv[1]).read_text()
if not t.lstrip().startswith(("#", ">")):
    i = t.find("\n# ")
    if i != -1: t = t[i+1:]
pathlib.Path(sys.argv[2]).write_text(t.lstrip())
PY
fi
grep -q '"gate": "FAILED"' "$META" 2>/dev/null && GATE_STATE=FAILED || GATE_STATE=PASS

# ---- S7: gbrain filing (draft-only by default) --------------------------------
GB_DRAFT="$WORK/gbrain-draft.md"
python3 - "$REPORT" "$META" "$GB_DRAFT" "$SLUG" <<'PY'
import sys, json
report, meta = open(sys.argv[1]).read(), json.load(open(sys.argv[2]))
from collections import Counter
verdicts = ""
body = f"""<!-- gbrain slug: research/{sys.argv[4]} | type: research-report | source: research-queue v1 -->
<!-- question: {meta.get('question','')} | date: {meta.get('date','')} | gate: {meta.get('gate','PASS')} -->

{report}
"""
open(sys.argv[3], "w").write(body)
PY
if [ "${RQ_GBRAIN_FILE:-0}" = 1 ] && command -v gbrain >/dev/null 2>&1; then
  gbrain put "research/$SLUG" < "$GB_DRAFT" && echo "S7: filed to gbrain as research/$SLUG" \
    || echo "WARN: gbrain put failed; draft remains at $GB_DRAFT"
else
  echo "S7: gbrain draft staged at $GB_DRAFT (set RQ_GBRAIN_FILE=1 to file)"
fi

mark_queue done
echo "[$(date)] DONE gate=$GATE_STATE report=$REPORT ($(wc -l <"$REPORT") lines)"
[ "$GATE_STATE" = PASS ]
