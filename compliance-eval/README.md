# compliance-eval — a real eval harness for the `shameless-script` skill

**Why this exists.** The 2026-06-20 deep-research on self-improving agents landed one load-bearing
finding: automated self-improvement only compounds when it's gated on a **hard, external, un-gameable
metric** — without one, ~half of "optimizations" score *below* baseline and you can't tell. This is
priority #1 from that report (`~/brain/projects/2026-06/self-improving-agents-research.md`): build the
gate before any optimizer.

Compliance is the cleanest first metric — a script either contains a banned claim or it doesn't.

## What it does

```
task prompts ──(generate via claude -p  OR  load files)──► scripts ──► SCORER ──► report ──► baseline diff
```

- **`scorer.py`** — deterministic, data-driven (reads `policy.json`) compliance scorer. The external
  verifier. Returns HARD violations (fail) and WARN flags (review). `violation_rate` = fraction of
  scripts with ≥1 HARD violation.
- **`policy.json`** — the Shameless banned/warn/allow canon as machine-checkable regex. **Edit this as
  policy evolves** — it's data, not code. Allow-list suppresses false flags on approved-but-risky
  language (prebiotic fiber, food noise, narrative weight-loss, "supports a healthy blood sugar response").
- **`gold/` + `gold_labels.json` + `test_scorer.py`** — **verify the verifier.** A labeled fixture set;
  the scorer is trusted only at precision = recall = 1.0 on HARD detection. Run this after any policy edit.
- **`run_eval.py`** — the runner: generate/score/baseline/diff. Catches **regressions** (a script that
  newly violates vs a stored baseline) and exits non-zero so it can gate CI / a cron / a skill change.

## Run it

```bash
cd ~/systems/compliance-eval

# 1. Verify the scorer is trustworthy (free, do this after ANY policy.json edit)
python3 test_scorer.py

# 2. Smoke the pipeline on labeled fixtures (free)
python3 run_eval.py --mode fixtures

# 3. The real eval: generate scripts from the skill and score them (costs tokens — 15 claude -p calls)
python3 run_eval.py --mode generate --save baseline_$(date +%Y%m%d) --save-scripts

# 4. After changing the skill / prompt / model, re-run and diff for regressions
python3 run_eval.py --mode generate --compare baseline_20260620
#    exit 1 = a regression was introduced (or generation errored)

# Score pre-generated scripts in a folder instead of generating
python3 run_eval.py --mode score-dir --dir /path/to/scripts
```

`--limit N` processes only the first N items (smoke tests). `--gen-cmd "..."` overrides the generator
(default `claude -p {prompt}`); `{prompt}` is substituted with the shell-quoted prompt.

## How it enacts the research

1. **External verifier, never self-grading** — the scorer is deterministic, not the same model judging
   its own output (the research's load-bearing caveat: LLM self-critique collapses; external checks work).
2. **Verify the verifier** — `test_scorer.py` gates the scorer itself against a labeled set before it's
   trusted, so the metric can't silently rot.
3. **Keep-best gate** — `--compare` turns "did this change help or hurt?" into a yes/no with an exit code,
   which is exactly what `feedback-synth` promotion and any future GEPA experiment need to avoid the
   49%-below-baseline trap.

## Extending

- New edge case slips through in production → add a fixture to `gold/`, label it in `gold_labels.json`,
  rerun `test_scorer.py`, fix `policy.json` until green. The gold set is the regression suite for the canon.
- New metric (field-fill accuracy, script quality) → clone the `scorer.py` + `test_scorer.py` pattern;
  `run_eval.py` is metric-agnostic (it just needs a scorer that returns pass/fail).

Canon sources: `brain/wiki/shameless/brand/compliance-guardrails.md`,
`brain/raw/brand-context/compliance_guide.md`, `memory/shameless_compliance_language.md`.
