# email-eval — eval-gate for the `email-copy` skill

First instance stamped from `../eval-factory.TEMPLATE.md`; adapted from the live
`~/systems/compliance-eval` harness (shameless-script gate). Read the template for the
full methodology (rule-tier triage, gold discipline, A/B protocol, gotchas).

## What it checks

`policy.json` encodes the email-copy canon:

- HARD regex rules: em/en-dash ban, code fences, labeled blocks ("Subject:"/"Preheader:"...),
  drug names, medical-cure claims, outcome guarantees, saturated phrases.
- HARD structure rules (new vs compliance-eval, implemented in `scorer.py`, configured in
  policy.json): `subject_count` (deliverable opens with exactly 5 numbered subject lines) and
  `cta_single` (exactly one arrow-convention CTA line; 0 = missing, 2+ = multi-CTA dilution).
- WARN rules: spam triggers, weak CTA verbs, numeric discount claims (review vs the 46 percent
  sub-gated ceiling), vague-curiosity subjects.
- NOT machine-checked (semantic, read the outputs): preheader-recaps-subject, first-line
  payoff of the subject, one-idea-per-paragraph, sequence position.

## Run it

```bash
cd ~/fable-window/artifacts/email-eval

python3 test_scorer.py                 # verify the verifier: must PASS 1.0/1.0 (free)
python3 run_eval.py --mode fixtures    # pipeline smoke on gold/ (free)

# real eval: 10 bait prompts through the installed email-copy skill (costs tokens)
python3 run_eval.py --mode generate --limit 3                       # smoke first
python3 run_eval.py --mode generate --save baseline_$(date +%Y%m%d) --save-scripts

# after any skill/prompt/model change
python3 run_eval.py --mode generate --compare baseline_YYYYMMDD    # exit 1 = regression
```

Every prompt in `prompts.jsonl` is a bait aimed at one rule (58%-off offer bait, drug-name
bait, em-dash style bait, multi-CTA bait, 8-subject-lines bait...) with the brand canon inlined
and the mandatory anti-preamble amendment appended. For head-to-head skill A/Bs, generate with
`--dangerously-skip-permissions` on BOTH sides and follow the template's A/B section.

Verified 2026-07-06: `test_scorer.py` PASS, HARD precision 1.000 / recall 1.000 over 15 fixtures.
