# Eval factory: stand up an eval-gate for ANY skill

Generalized from `~/systems/compliance-eval` (the shameless-script gate) and the two A/B rounds
that stress-tested it (`eval-ab.RESULTS.md`, `eval-ab-clean.RESULTS.md`). Follow this to build a
deterministic, un-gameable quality gate for any generating skill (scripts, emails, landing pages,
briefs, task descriptions). First working instance from this template: `artifacts/email-eval/`
(gate for the `email-copy` skill).

## Why a gate at all

The 2026-06-20 self-improving-agents research finding that started this: automated improvement
only compounds when gated on a hard, EXTERNAL, deterministic metric. Without one, roughly half of
"optimizations" land below baseline and you cannot tell. LLM self-critique collapses; a regex +
structural scorer does not. Build the gate BEFORE any optimizer, prompt tweak, or skill rewrite
you want to trust.

## The five parts (one directory per skill)

```
<skill>-eval/
  policy.json       the skill's canon as machine-checkable rules (DATA, not code)
  scorer.py         deterministic scorer: regex rules + structural checks, reads policy.json
  gold/             labeled fixture texts, one per rule (clean + violation + tricky-allowed)
  gold_labels.json  ground truth per fixture: exact HARD rule_id set + warn_includes/excludes
  test_scorer.py    verify-the-verifier: asserts precision = recall = 1.0 on HARD detection
  prompts.jsonl     bait prompts: each one tempts the skill toward a specific rule violation
  run_eval.py       runner: generate | fixtures | score-dir modes, baseline save/compare, exit codes
  baselines/ runs/  saved reports and generated outputs (gitignore-able)
```

### 1. policy.json: canon as data

Three-plus sections, all read by the scorer at init:

- `hard`: definite violations. Each rule = `{id, why, patterns[]}` with case-insensitive regex.
  A script/email with any HARD hit fails. `violation_rate` = fraction of outputs with >= 1 HARD.
- `warn`: review-before-publish flags. Reported, never fail an output.
- `allow`: approved-but-risky phrases. Any HARD/WARN match whose span sits INSIDE an allow phrase
  is suppressed. This is what keeps canon-approved language ("prebiotic fiber", "food noise",
  narrative weight loss) from false-flagging. Without an allow list a compliance regex set is
  unusable on real copy.
- `structure` (new in email-eval, add when the skill has a shape contract): deterministic
  non-regex checks (count of leading numbered lines, count of CTA lines, required blocks).
  Config in policy.json, implementation in scorer.py, same Finding/rule_id plumbing so
  test_scorer.py and run_eval.py need zero changes.
- `_meta.policy_version` + `_meta.sources`: date-stamp every policy edit and cite where the rule
  came from (Tomas ruling, wiki canon, production incident). Policies rot silently otherwise;
  the 2026-07-02 ledger caught policy.json 4 rules behind canon.

Rule-design triage. Every canon rule falls in one of three tiers; know which before writing it:

1. GREPPABLE: a phrase ban ("real fruit", drug names, em dash). Regex it, HARD or WARN.
2. STRUCTURAL: a shape contract (exactly 5 subject lines, single CTA, no labeled blocks).
   Code it as a structure check; regex alone cannot count.
3. SEMANTIC (policy_gap): context-dependent judgment ("do not lead with the low-calorie absolute
   on a sour SKU", "canon stat beats the brief's stale stat"). Do NOT force a regex; it will
   false-flag. Instead: (a) tag the gold/bait entry `policy_gap: true`, (b) keep a one-line grep
   sweep for the fingerprints (the compliance HOWTO step 6 pattern), (c) eyeball those cases.
   A scorer PASS on a policy_gap case is necessary, not sufficient.

### 2. scorer.py: the external verifier

Copy `~/systems/compliance-eval/scorer.py` (or `artifacts/email-eval/scorer.py` if you need
structure checks) and change nothing but the docstring. Properties that must survive any edit:

- Deterministic. Same text in, same findings out. No LLM anywhere in the scoring path.
- Data-driven. Reads policy.json; canon evolves without code edits.
- Whitespace-tolerant. Literal spaces in patterns compile to `\s+` so copy that wraps a phrase
  across a line break still matches.
- Allow-list suppression runs on every match before it becomes a finding.
- Findings carry `rule_id`, severity, the exact matched span, and offsets, so a failure is
  diagnosable from the report alone.

### 3. gold/ + gold_labels.json + test_scorer.py: verify the verifier

The scorer is trusted ONLY at precision = recall = 1.0 on HARD detection over the gold set.
On a small curated set, any miss or false-flag is a real bug, not noise. Discipline:

- One fixture per rule minimum: it fires exactly that rule and nothing else. Every violation
  fixture must be shape-correct otherwise, or the structural rules contaminate its label.
- Plus: 2+ fully clean fixtures, 1+ "tricky allowed" fixture stuffed with allow-list phrases
  (guards the allow list), 1 multi-violation fixture (guards dedup and set comparison),
  and WARN fixtures with `warn_includes` / `warn_excludes` (excludes catch over-broad warns).
- After ANY policy.json edit: `python3 test_scorer.py` must print PASS before anything else runs.
  Non-negotiable; a policy edit that breaks gold is either a bad regex or a stale label, and
  either one means the gate is lying.
- New edge case slips through in production: add a fixture, label it, watch test_scorer FAIL,
  fix policy.json until green. The gold set IS the regression suite for the canon.
- Never merge bait-prompt gold (expected results for a compliant GENERATION) into
  gold_labels.json (expected scorer output for FIXTURE texts). They grade different things;
  mixing them crashes test_scorer (no fixture file) or corrupts precision.

### 4. prompts.jsonl: bait design

Each line: `{"id", "angle", "format", "prompt"}`. Principles learned the hard way:

- Every prompt is a bait aimed at one rule. A generic "write an email" tests nothing; "the brief
  suggests 58 percent off" tests offer discipline. Keep 1-2 clean control prompts.
- Inline the brand canon in the prompt if the skill is brand-agnostic (email-copy, dr-script).
  The bait must contradict the canon so you can see which one wins.
- MANDATORY anti-preamble amendment on every prompt (the meta-preamble contamination lesson,
  eval-ab 2026-07-04): both sides of the first A/B prepended notes naming the bans they avoided
  ("no real fruit, no Made in USA") and the grep scorer flagged the MENTION itself. Most
  hard-fails were this false positive. Append verbatim:
  "Output ONLY the deliverable itself. No preamble, no notes, no compliance commentary; any
  non-deliverable text is a failure."
  Score deliverable text only; a strategist note that names a banned phrase is an
  instruction-following failure, not a compliance failure, and must be counted as the former.

### 5. run_eval.py: the runner and gate

Copy it; it is metric-agnostic (needs only a scorer returning pass/fail per text). Modes:
`fixtures` (free smoke), `score-dir` (score pre-generated texts), `generate` (claude -p per
prompt, then score). Flags: `--save LABEL` writes baselines/LABEL.json, `--compare LABEL` diffs
and exits 1 on any REGRESSION (an output that newly violates vs baseline), `--limit N` smoke,
`--save-scripts` keeps outputs in runs/LABEL/, `--gen-cmd` swaps the generator, `--rule` injects
a candidate guidance line into every prompt (keep-best gate for feedback promotion).

Exit-code contract: 0 = no regressions and no generation errors; 1 otherwise. A nonzero
violation rate alone does NOT fail the run; it is the metric you track over time.

## Stand-up checklist (new skill, ~1-2h + one generate run)

1. Read the skill's SKILL.md and source memories; list every rule as greppable / structural /
   semantic (tier triage above).
2. Write policy.json: hard, warn, allow, structure, `_meta` with version + sources.
3. Copy scorer.py (+ structure scan if tier-2 rules exist), test_scorer.py, run_eval.py.
4. Write gold fixtures + gold_labels.json per the discipline in part 3.
5. `python3 test_scorer.py` until precision = recall = 1.0. Do not proceed before this.
6. `python3 run_eval.py --mode fixtures` (free end-to-end smoke).
7. Write prompts.jsonl baits with canon inline + the anti-preamble amendment.
8. `python3 run_eval.py --mode generate --limit 3` smoke, then full run with
   `--save baseline_YYYYMMDD --save-scripts`. That baseline is the gate every future skill /
   prompt / model change is compared against.

## A/B methodology (from eval-ab-clean, the run that got it right)

When comparing skill versions (candidate vs live), the naive run produces invalid numbers.
The first A/B failed three ways; the clean protocol fixes all of them:

1. FULL head-to-head coverage. Same N prompts, both sides, same day. run_eval's resume
   semantics can silently split coverage (live scored n01-n14, candidate n15-n20: not a
   comparison). Delete or verify-complete any stale run dirs first; if you keep a prior
   complete side, disclose it and confirm same flags / same amendment / no error contamination.
2. IDENTICAL permissions both sides. Generate with `claude -p --dangerously-skip-permissions`
   so both skills can read memory canon. The first A/B ran without it and the live skill
   couldn't read canon files (said so in 8/14 outputs): permission skew, not skill quality.
3. Anti-preamble amendment on ALL prompts, both sides (see part 4).
4. Candidate injection without installing: wrapper script that inlines the candidate SKILL.md
   via `--append-system-prompt` with a header saying the inline version supersedes the installed
   one. Spot-check one output for the candidate's fingerprints (its newer rules) to confirm it
   actually drove generation.
5. Grade on FOUR axes, not just the scorer: (a) scorer HARD/WARN counts, (b) gold-grader
   pass/fail vs expected per-case labels including warn_excludes, (c) the scorer-blind grep
   sweep over saved outputs (policy_gap fingerprints), (d) a human/agent READ of the policy_gap
   cases. In eval-ab-clean both sides scored 0 HARD; the entire separation lived in axes b-d.
6. Work in a COPY of the harness (`~/fable-window/eval-work/...`), never the live dir.
7. Disclose every method deviation in the results doc; an undisclosed shortcut is how invalid
   numbers get trusted.

## Operational gotchas (box-specific, all cost real runs to learn)

- Headless discipline: generation runs are synchronous foreground loops. Never background a
  child and wait for a notification (none exists; two agents died this way). Chunk long runs
  into resumable, size>0-skip driver loops if the session budget is tight.
- `claude -p` with rc 0 and ZERO output is a known silent failure; validate non-empty before
  scoring, count empties as generation errors.
- Budget: one `claude -p` per prompt, 300s timeout, sequential. 20 prompts = 20-60+ min and
  real window tokens. `--limit 3` first, always. Usage-limit hits are transient (retry), not
  failures.
- Prompt goes via the documented arg substitution ({prompt} is shell-quoted); never positional
  after `--allowed-tools`.

## Instances

| gate | skill under test | status | notes |
|------|-----------------|--------|-------|
| `~/systems/compliance-eval` | shameless-script | live, scorer 1.0/1.0 | regex + allow list; policy_gap swept by HOWTO step 6 grep |
| `artifacts/email-eval` | email-copy | artifact, scorer 1.0/1.0 | adds `structure` checks (subject count, single CTA) |
