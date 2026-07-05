# eval-ab RESULTS (2026-07-04, scored deterministically after 07c/07d agent failures)

## Verdict: CANDIDATE SHIPPED on qualitative evidence; numeric A/B was invalid.

## Why the numbers are invalid
- Split coverage: live baseline scored n01-n14 only, candidate n15-n20 only (run_eval resume semantics). Not head-to-head.
- Meta-commentary contamination: both skills prepended notes naming the bans they avoided ("no real fruit, no Made in USA"); the grep scorer flags the mention itself. Most hard-fails are this false positive.
- Permission skew: gen commands ran claude -p WITHOUT permission bypass, so the LIVE skill could not read memory canon files (it says so in 8/14 outputs) while the CANDIDATE has canon baked in. Distorts live results, but also demonstrates the candidate design goal.

## Qualitative signal (real, from reading outputs)
- cand n15: refused the brief's 58% off, corrected to 46% sub-gated ceiling (canon-beats-brief worked).
- cand n20: caught stale 29g All-Stars stat, wrote 26g, flagged the override.
- cand n18: rerouted banned color-origin question to a compliant flavor walk.
- live runs: repeatedly degraded to baked-in-KB guesses when memory reads were blocked.

## Follow-up
Clean A/B queued as night-3 task 27: full 20x2, gen with --dangerously-skip-permissions, prompts amended to forbid meta-preambles, scorer applied to deliverable text only.
