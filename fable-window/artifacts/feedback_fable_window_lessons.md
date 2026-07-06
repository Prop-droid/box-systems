---
name: fable-window-lessons
description: 9 measured lessons from the 2026-07 fable-window (40+ overnight tasks) on authoring skills, evals, and automation with Opus; each backed by evidence from the window
metadata:
  type: feedback
---

Meta-distill of the fable-window (2026-07-02 to 2026-07-05): what measurably made outputs better, as transferable canon for future skill/eval/automation authoring. Sources: `~/fable-window/{RULES.md,REPORT.md,REPORT-night3.md}`, `artifacts/{_ledger.md,eval-ab.RESULTS.md,eval-ab-clean.RESULTS.md,VERIFY.md,VERIFY-night3.md}`. Related: [[feedback-define-verification-target]], [[feedback-confidence-check-before-chains]], [[project-compliance-eval-harness]], [[project-fable-window]].

## 1. Bake canon into the skill; do not rely on runtime memory reads
**Why:** The only clean A/B of the window proved it. Old shameless-script (canon via memory recall) vs new (canon baked in): gold grader 19/20 vs 20/20, warn leakage 7 vs 2, baits taken 3 vs 0 (blood-sugar framing, 58% offer note, "only 70 calories" on a 70-90 cal SKU). The invalid first A/B showed the failure mode directly: when memory reads were blocked, the old skill degraded to guesses in 8/14 outputs. [eval-ab-clean.RESULTS.md; eval-ab.RESULTS.md]
**How to apply:** When a skill depends on facts (stats, ceilings, bans, IDs), write them into the SKILL.md body with a "canon beats brief" rule. Memory files are for discovering canon, not for load-bearing recall at generation time. Same move worked for clickup-task-creator (six memory gotchas folded in, "zero memory recall needed").

## 2. Kill-criteria checklists beat vibe critique
**Why:** The rewritten skills replaced "critique internally" with named hard kills (compliance gate, DSI test promoted from fail-3+ to hard kill, ship bar). The A/B wins map one-to-one onto those gates: new skill rerouted blood-sugar bait, corrected the brief's 58% to the 46% canon ceiling, avoided the absolute calorie claim. The playbooks got 5-6 kill criteria each and survived independent verification unchanged. [_ledger tasks 01/02/23; eval-ab-clean baits-taken section]
**How to apply:** Every generative skill gets an explicit KILL list (binary, checkable, named failure modes) plus a ship bar. "Fail N of M" soft scoring lets weak output ship; hard kills do not.

## 3. Eval-gate before ship, and layer the scoring
**Why:** The regex scorer alone could NOT separate the two skills (both 0 HARD on all 20); the entire signal came from the layers above it: gold semantic grader (n03), scorer-blind grep (n15), and human read of number baits (n19). Meanwhile the eval harness itself stayed trustworthy because every policy patch had to keep test_scorer.py at precision=recall=1.0 (ebda053-73da066, e18ed86-bb5bcd5). [eval-ab-clean.RESULTS.md interpretation; _ledger tasks 04/07b/22]
**How to apply:** Ship skill changes only through an eval: regex scorer for greppable bans, gold labels for semantic baits, a scorer-blind grep sweep, and a read pass for non-regexable baits. Ground baits in real canon traps (stale stats, wrong-number briefs, adaptation of violating source ads), not invented cases. Keep the scorer's own fixture suite at 1.0/1.0 as a hard invariant.

## 4. Pin the output contract in the eval prompt
**Why:** The first A/B was ruled invalid partly because both skills prepended meta-notes naming the bans they avoided, and the grep scorer flagged the mention itself (false positives). One amendment line on all 40 prompts ("Output ONLY the deliverable... any non-deliverable text is a failure") eliminated the false positives AND converted the one remaining note into a genuine, scoreable finding. [eval-ab.RESULTS.md flaw 2; eval-ab-clean.RESULTS.md n15]
**How to apply:** Every eval prompt states the deliverable contract explicitly so scorers measure the deliverable, not narration. Also equalize permissions across arms (the first A/B's other fatal flaw was one side unable to read memory canon).

## 5. Headless runs are one-shot: finish synchronously
**Why:** The only agent failures of the window (07c, 07d) died waiting on background jobs and notifications that never arrive in `claude -p`. This became RULES amendment 7; after it, nights 3-4 ran exit=0 across the board and task 27 completed in synchronous foreground chunks. [RULES.md rule 7; REPORT.md; eval-ab-clean method deviations]
**How to apply:** In any headless prompt or RULES file: no background jobs, no awaiting re-invocation, finish everything in-process. Long work goes into resumable chunks (size>0-skip drivers) so a killed run resumes instead of restarting.

## 6. Deterministic scripts do the waiting; agents do only the judgment
**Why:** Everything reliability-shaped was deterministic and it all held: driver.sh handled 16 retries over 8h and marked LIMIT-GAVE-UP cleanly; gen_driver.py made generation resumable and budget-safe; atria-weekly ships a deterministic python fallback so a report always lands even if headless claude fails 3x; the first A/B was salvaged by scoring deterministically after the agent runs failed. Agent calls were reserved for generation and semantic reading. [_ledger tasks 15/23/27; playbook_overnight_harness.md]
**How to apply:** Retry loops, polling, resume semantics, scoring, and fallbacks are scripts with constants at the top. Never spend an LLM call on waiting, retrying, or anything a grep/diff can decide. Design the fallback so the pipeline degrades to a worse report, not to silence.

## 7. Independent verify pass catches mechanical rot the authors cannot see
**Why:** VERIFY.md found 4 of 7 fresh SKILL.md files had invalid YAML frontmatter (unescaped `word: word` in a plain-scalar description) that every authoring pass had missed; fixed mechanically, all 7 then parsed. VERIFY-night3 independently re-ran the scorer, re-diffed 133/133 memory-link parity, nft -c parsed both rulesets, git apply --check'd both patches, and re-grepped a claimed fact ("no cron uses these keys"). Cost: one small task per night; caught real defects both nights. [VERIFY.md; VERIFY-night3.md]
**How to apply:** Every batch of authored artifacts gets a separate verify task with named checks (parse the YAML/JSON/nft, re-run the test suite, diff parity, re-verify one claimed fact per artifact). Fix mechanical issues in place; flag substantive ones for a human. Never let the authoring session self-certify.

## 8. Additive staging plus a baseline before every live write
**Why:** Default artifacts-only (RULES #2), with each live exception individually authorized and baselined first: git commits around both compliance-eval patches, sha256 file snapshots around the 16-file wiki edit when git was unavailable (graceful degrade, not a skipped baseline), crons staged but never enabled, every apply-checklist step shipped with its backup command. 40+ tasks, several live surfaces touched, zero unrecoverable mistakes and instant rollback paths everywhere. [RULES.md rules 2/8/9; _ledger tasks 07b/22/30; both REPORT apply checklists]
**How to apply:** Automation writes to a staging dir by default; live writes need explicit authorization plus a committed/hashed baseline immediately before and after. Hand off as a risk-ordered apply checklist where every step embeds its own backup command.

## 9. Write rule scope explicitly or pay for the ambiguity every night
**Why:** RULES #5 ("no em dashes in any copy-facing text") left "copy-facing" undefined. Result: the same policy conflict was re-litigated in three ledger entries, flagged by both verify passes (~276 + 85 dashes), and escalated as an open question in both reports; it never resolved because the rule, not the work, was ambiguous. The night-3 playbooks sidestepped it only by going dash-free entirely. [VERIFY.md; VERIFY-night3.md; REPORT.md open q1]
**How to apply:** When authoring RULES/eval policies for autonomous runs, define scope with an include/exclude list and one example of each. Any rule an agent must interpret will be interpreted differently by every agent, and verify passes will flag the disagreement forever instead of the real defects.
