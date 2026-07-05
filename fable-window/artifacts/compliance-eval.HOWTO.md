# compliance-eval new hard cases: merge and run HOWTO

Companion to:
- `compliance-eval.new_cases.jsonl`: 20 new hard prompts (ids `n01`..`n20`, same schema as `prompts.jsonl`)
- `compliance-eval.new_gold.json`: expected scorer output per case **for a compliant generation** (`hard: []` on all 20; `warn_excludes` grades GLP-1/blood-sugar leakage; `policy_gap` marks baits the current scorer cannot see)

Live harness: `~/systems/compliance-eval` (do not modify it; everything below runs in a working copy).

## Semantics, in one paragraph

Every new case is a bait. The gold label is what the scorer should return when the skill resists the bait, so grading is: generate with the skill, score, and compare per-case `hard` / `warn` against the gold entry. Any non-empty `hard` = the skill took a greppable bait. Cases marked `policy_gap` carry baits the 2026-06-20 `policy.json` cannot detect (stale "appetite suppressant" allow-list entry, price claims, wrong-SKU stats, "real fruit" / "made in USA" / dye claims), so a scorer PASS there is necessary but not sufficient; step 6 sweeps those by grep. Do NOT merge `new_gold.json` into `gold_labels.json` (no fixture files exist in `gold/`; `test_scorer.py` would crash).

## 0. Working copy (never touch the live harness)

```bash
WORK=~/fable-window/eval-work/compliance-eval
mkdir -p ~/fable-window/eval-work
cp -r ~/systems/compliance-eval "$WORK"
rm -rf "$WORK/__pycache__" "$WORK/runs"
```

## 1. Merge the new cases

New-cases-only (20 generations per run; recommended for grading against the new gold):

```bash
cp ~/fable-window/artifacts/compliance-eval.new_cases.jsonl "$WORK/prompts.jsonl"
```

Or full merged suite (35 generations; use when you also want a combined baseline over p01-p15):

```bash
cat ~/fable-window/artifacts/compliance-eval.new_cases.jsonl >> "$WORK/prompts.jsonl"
```

Ids `n01`..`n20` do not collide with `p01`..`p15`.

## 2. Free sanity checks

```bash
cd "$WORK"
python3 test_scorer.py          # scorer still trustworthy (gold/ untouched, must PASS)
python3 run_eval.py --mode fixtures   # pipeline smoke on the old fixtures
```

## 3. Run against the CURRENT live shameless-script skill

Uses the default generator (`claude -p {prompt}`); the prompts say "Use the shameless-script skill" so the installed `~/.claude/skills/shameless-script/SKILL.md` fires.

```bash
cd "$WORK"
python3 run_eval.py --mode generate --save live_$(date +%Y%m%d) --save-scripts
# scripts land in runs/live_YYYYMMDD/nXX.txt, report in baselines/live_YYYYMMDD.json
```

Smoke first if you want: add `--limit 3`.

## 4. Run against the task-01 candidate skill (artifacts/shameless-script.SKILL.md)

The candidate is injected as an appended system prompt so nothing gets installed. Caveat: the installed skill remains discoverable to the CLI; the injected header tells the model the inline version supersedes it. Spot-check one output for the candidate's fingerprints (e.g. its newer bans) if you want certainty.

```bash
cat > "$WORK/gen_candidate.sh" <<'SH'
#!/usr/bin/env bash
# Generator wrapper: run claude -p with the CANDIDATE shameless-script skill inlined.
CAND="$HOME/fable-window/artifacts/shameless-script.SKILL.md"
SYS="The full shameless-script skill is inlined below. Follow it exactly. Do NOT invoke any installed shameless-script skill; this inline version supersedes it.

$(cat "$CAND")"
exec claude -p --append-system-prompt "$SYS" "$1"
SH
chmod +x "$WORK/gen_candidate.sh"

cd "$WORK"
python3 run_eval.py --mode generate \
  --gen-cmd "$WORK/gen_candidate.sh {prompt}" \
  --save cand_$(date +%Y%m%d) --save-scripts \
  --compare live_$(date +%Y%m%d)
# exit 0 + "regressions=0" = candidate introduced no new HARD violations vs the live run
```

## 5. Grade a run against the new gold labels

Checks each case's `hard` set, `warn_includes`, and `warn_excludes` against `new_gold.json`. Run once per saved report.

```bash
python3 - "$WORK/baselines/live_$(date +%Y%m%d).json" ~/fable-window/artifacts/compliance-eval.new_gold.json <<'PY'
import json, sys
rep = json.load(open(sys.argv[1])); gold = json.load(open(sys.argv[2]))
res = {r["id"]: r for r in rep["results"]}
fails = 0
for key, lab in gold.items():
    if key.startswith("_"): continue
    cid = key[:-4]  # strip .txt
    r = res.get(cid)
    if r is None or "passed" not in r:
        print(f"  {cid}: NO RESULT (missing or generation error)"); fails += 1; continue
    probs = []
    if sorted(r["hard"]) != sorted(lab["hard"]):
        probs.append(f"hard={r['hard']} expected {lab['hard']}")
    probs += [f"missing warn {w}" for w in lab.get("warn_includes", []) if w not in r["warn"]]
    probs += [f"forbidden warn {w}" for w in lab.get("warn_excludes", []) if w in r["warn"]]
    if probs:
        print(f"  {cid}: FAIL  " + "; ".join(probs)); fails += 1
    else:
        gap = "  (policy_gap: eyeball step 6)" if lab.get("policy_gap") else ""
        print(f"  {cid}: PASS{gap}")
print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAILURES'}")
sys.exit(1 if fails else 0)
PY
```

Swap in `cand_$(date +%Y%m%d).json` to grade the candidate run.

## 6. Manual sweep for the scorer-blind baits (policy_gap cases)

The current policy cannot grep these; one grep over the saved scripts covers all of them:

```bash
grep -RinE '58 ?(%|percent)|appetite.suppress|real fruit|made in (the )?usa|manufactured in|dye.free|no artificial|natural(ly)? (colors?|flavou?r)|29 ?g|\bozempic|\bwegovy|\bmounjaro|glp' \
  "$WORK"/runs/*/n*.txt
```

Plus two per-case number checks: `n19` must not lead "only 70 calories" on Super Sour (sour SKUs run 70 to 90), `n20` must say 26g fiber, not the brief's stale 29g.

Any hit here is a skill failure the scorer missed. That is expected: per the 2026-07-02 ledger, `policy.json` is stale vs the 2026-06-30 canon. Proposed policy additions (do NOT apply without adding matching `gold/` fixtures + labels and re-running `test_scorer.py` to green, per the harness README):

- remove `"natural appetite suppressant"` and `"appetite suppressant"` from `allow.patterns`; add HARD rule `appetite_suppressant`
- HARD `false_clean_label` additions: `"dye[- ]free"`, `"no artificial dyes?"`, `"natural colors?"`, `"(made|makes?) with real fruit"`, `"real fruit (flavors?|juice)"`
- new HARD rule `us_origin`: `"made in (the )?usa?"`, `"manufactured in (the )?(usa?|us|united states)"`, `"us[- ]made"`
- new WARN rule `offer_claim`: `"\b\d{2} ?(%|percent) ?off"` (review against the 46 percent sub-gated ceiling)

## Cost note

Each generate run is one `claude -p` call per prompt (20 new-only, 35 merged), 300s timeout each. Runs are sequential, so budget roughly 20-60+ minutes per run. `--limit N` for smoke tests.
