# compliance-eval policy patch (2026-07-03)

Live harness patch (authorized exception to RULES #2, approved by Tomas 2026-07-02).
Repo: `~/systems/compliance-eval`. Git baseline committed first (`ebda053`), patch
committed after (`73da066`).

## What changed and why

### policy.json
1. **appetite suppressant: allow-list -> HARD ban.** Removed both `natural appetite
   suppressant` and `appetite suppressant` from `allow.patterns`. Added new HARD rule
   `appetite_suppressant` (pattern `appetite suppressant`). The term was banned
   2026-06-30. `kills cravings` / `curbs cravings` / `keeps you full` / `feel full`
   stay allowed (only the appetite-suppressant phrasing was banned).
2. **New 2026-06-30 bans added:**
   - HARD `real_fruit` (`real fruit`) - no real fruit in the formulation.
   - HARD `made_in_usa` - `made in (the) usa`, `made in america`,
     `manufactured in (the) usa`, `american-made`, `us-made`. Allowed exception
     `packed in the US` added to the allow-list (and it does not match any
     made-in pattern, so it passes clean).
   - `false_clean_label` extended with `no artificial dyes`, `natural flavors`,
     and `dye-free` / `dye free` (`dye[-\s]+free`, so line wraps still match).
     `no artificial colors/flavors`, `no artificial sweeteners`, `naturally flavored`
     were already covered.
3. **Sweetener guard.** New HARD rule `false_ingredient_allulose` (`allulose`). Core
   bags use sucralose + erythritol, not allulose (Tomas 2026-07-02), so any allulose
   claim is factually wrong. `no artificial sweeteners` remains banned (unchanged).
4. **70-90 calories left ALLOWED** - no calorie pattern added; some bags are 90 cal.
5. `policy_version` bumped `2026-06-20` -> `2026-07-03`; `_meta.sources` and `_meta.note`
   updated to record the new bans.

### gold/ fixtures + gold_labels.json
- **Rewrote `tricky_allowed_01.txt`** to drop the now-banned appetite-suppressant
  sentence; it stays a genuinely-allowed tricky case (food noise, narrative weight
  loss, supports-a-healthy-blood-sugar-response, prebiotic fiber, keto). Its label is
  unchanged (hard [], warn_excludes blood_sugar_bare).
- **Added 6 fixtures** so the new canon is actually tested (a ban with no test is a gap):
  - `violation_appetite_01.txt` -> hard [appetite_suppressant]
  - `violation_realfruit_01.txt` -> hard [real_fruit]
  - `violation_madeusa_01.txt` -> hard [made_in_usa]
  - `violation_allulose_01.txt` -> hard [false_ingredient_allulose]
  - `violation_dyefree_01.txt` -> hard [false_clean_label] (dye-free + natural flavors + no artificial dyes)
  - `tricky_allowed_02.txt` -> hard [] (proves `packed in the US` and `90 calories` pass clean)

## Verification (ran against the gold set, passes clean)

```
$ python3 test_scorer.py
Fixtures: 15
HARD detection  precision=1.000  recall=1.000  (TP=15 FP=0 FN=0)
RESULT: PASS - scorer is trustworthy     EXIT=0

$ python3 run_eval.py --mode fixtures
Items 15 | scored 15 | errors 0 | pass 5/15 | violation_rate 0.667 | HARD 25 WARN 2   EXIT=0
```

5 pass (clean_01, clean_02, tricky_allowed_01, tricky_allowed_02, warn_glp1_01);
the 10 violation fixtures correctly FAIL. Existing fixtures unaffected by the new rules
(verified: `warn_glp1_01`'s "your appetite is smaller" does not match `appetite suppressant`).

## Open questions
1. Did not run `--mode generate` (costs ~15 `claude -p` calls) - task asked to verify
   against the gold set, which passes. Run a real generate + `--save` if you want a fresh
   scored baseline under the new policy.
2. Kept `kills cravings` / `keeps you full` allowed. If those are also now considered
   drug-effect claims, add them to HARD and I will update fixtures.
3. `made_in_usa` patterns are manufacturing-specific. If broader US-origin phrasing
   ("proudly American", "US-sourced") should also fire, extend the pattern list.
