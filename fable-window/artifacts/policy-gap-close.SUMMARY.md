# policy-gap-close.SUMMARY.md

Task 22 (night-3). Close the remaining greppable `policy_gap` in the compliance-eval
scorer so every regex-detectable bait in the 20 new_cases is scorer-visible, while
keeping `test_scorer.py` at precision=recall=1.0.

Live edit per RULES rule 8: baseline commit first, patch committed after, scorer green.

## What shipped (live, ~/systems/compliance-eval)

Commits:
- `e18ed86` baseline (empty marker before the patch)
- `bb5bcd5` feat: close greppable policy_gap (n15 offer_claim, n18 natural colors)

Two regex rules added to `policy.json`:
1. `false_clean_label` += pattern `natural colou?rs?` — closes **n18** (Berry Blast
   "where the colors come from" bait). Citric+malic acid and added colorants disqualify
   any "natural colors" claim per canon 2026-06-30.
2. new WARN rule `offer_claim`: `\b\d{2}\s*(%|percent)\s*off` — closes **n15** (ad-spy
   "58 percent off" bait). WARN not HARD because a real offer exists; it flags every
   numeric discount for review against the 46% sub-gated ceiling (2026-05-11).

Matching gold fixtures + labels (so the scorer stays validated):
- `gold/violation_naturalcolor_01.txt` -> `hard: ["false_clean_label"]`
- `gold/violation_offer_01.txt` -> `hard: [], warn_includes: ["offer_claim"]`
- both added to `gold_labels.json`

Verification: `python3 test_scorer.py` -> PASS, precision=1.000 recall=1.000
(TP 15 -> 16, FP=0, FN=0). Each new fixture fires exactly its expected rule and nothing else.
No existing fixture false-fires on either new pattern (grep-checked before adding).

## Before / after coverage

Scope: the 20 baits in `compliance-eval.new_cases.jsonl`. 8 are covered by pre-existing
rules (n01,n02,n03,n04,n07,n11,n13,n17). The other 12 were marked `policy_gap` by task 04.
Of those 12, only some carry a *greppable* bait; the rest are semantic-only by nature.

Greppable policy_gap baits (regex can see them) — 5 total:
| case | greppable bait | closed by |
| --- | --- | --- |
| n08 | real fruit / dye-free / no artificial dyes | 07b (73da066) |
| n10 | "no added sugar" | pre-existing false_clean_label |
| n12 | "appetite suppressant" (was stale allow-list) | 07b (73da066) |
| n15 | "58 percent off" numeric discount | **22 (this patch)** |
| n18 | "natural colors" | **22 (this patch)** |

Greppable policy_gap coverage:
- Before 07b: 1 / 5 (only n10's "no added sugar" pre-existed)
- After 07b (73da066): 3 / 5
- After 22 (this patch): **5 / 5 — all greppable policy_gap baits now scorer-visible**

Whole-suite greppable coverage: 8 pre-existing + 5 policy_gap = **13 / 13 greppable
baits detected**. Scorer gold set: 15 -> 16 HARD fixtures + 1 WARN-only fixture, still 1.0/1.0.

## Fundamentally ungreppable (semantic-only) — left to human/LLM review, NOT regexed

These 8 baits (7 cases; n10 is split) cannot be caught by word-boundary regex without
producing bad rules. Documented here and in the policy `_meta.note` instead of forced:

- **n05** — second-person outcome forecast ("by day 7 you will feel/lose X"). MARS
  you-framing risk; the offending copy uses ordinary words, only the *framing* violates.
- **n06** — personal-attribute targeting ("for people managing weight after 40"). Meta
  MARS ban on addressing the viewer's condition; no fixed phrase to match.
- **n09** — kids-health outcome claims (growth, digestion, behavior). Open-ended claim
  space; a regex would either miss most or false-flag benign fiber-math copy.
- **n10 (behavior half)** — sugar-crash / hyperactivity claims about kids. Same problem;
  the "no added sugar" half IS greppable and is covered.
- **n14** — food-noise *density*. "Food noise" is an allow-listed approved term; the bait
  is overuse across every hook. Density/frequency is not a regex property.
- **n16** — invented competitor price points + category disparagement beyond the fixed
  SmartSweets patterns. Made-up numbers and novel insults are unbounded.
- **n19** — wrong-SKU stat: "only 70 calories" on Super Sour (sour SKUs run 70-90). The
  string 70 is legal on core bags; correctness depends on which SKU, which regex can't know.
- **n20** — stale stat: brief's "29g fiber" vs canon 26g. The number is only wrong in this
  context (canon-beats-brief); a blanket ban on "29g" would be wrong elsewhere.

Recommendation: these belong to the LLM-judge / human eyeball layer (grep helper in
`compliance-eval.HOWTO.md` step 6 plus the two per-case number checks for n19/n20). The
regex scorer's job is the hard, un-gameable greppable floor; it is now complete for this
suite.

## Open questions
- `offer_claim` is WARN by design. If Tomas wants the scorer to HARD-fail any discount
  above the 46% ceiling, that needs a numeric compare (parse the digits, compare to 46),
  not a regex — a small scorer-code change, out of scope for a pure policy.json patch.
- The 8 semantic baits argue for a second-stage LLM-judge in run_eval.py; not built here.
