# Wiki Canon-Conflict Fix — Apply Summary (task 30)

**Date:** 2026-07-05
**Source fix list:** `~/fable-window/artifacts/wiki-conflict-sweep.md`
**Scope:** Tier 1 (12 compliance-dangerous) + Tier 2 (5 stale-stat). Tier 3 (3 tone findings 3.1/3.2/3.3) intentionally SKIPPED per task instruction.
**Authority:** RULES.md rule 9 (night-4 live exception — task 30 may edit wiki files under `~/brain` per the sweep doc).

## Baseline / rollback
`~/brain` is NOT a git repository (confirmed via `git rev-parse`; heavy `raw/` assets make `git init` on the canonical root inadvisable). Degraded gracefully per RULES rule 6: instead of `git commit`, took a file-level baseline snapshot of all 16 touched files before editing and a post-edit snapshot after.
- Baseline: `~/fable-window/artifacts/wiki-fix-baseline/` (16 files) + `wiki-fix-baseline.sha256`
- Post-edit: `~/fable-window/artifacts/wiki-fix-postedit/` (16 files)
- Rollback = copy any baseline file back over its `~/brain` path.

All 26 verification greps (17 findings, several multi-edit) PASS. 16/16 target files modified, zero collateral files touched.

## Per-finding table

| Finding | File | Status | Verify |
|---|---|---|---|
| 1.1 appetite-suppressant policy block + Now-Permitted line + hard stop | wiki/shameless/brand/compliance-guardrails.md | Applied (3 edits: policy block replaced, permitted line removed, hard stop added) | PASS |
| 1.2 "Natural appetite suppressant" permitted tier → hard stop | wiki/shameless/working-cards/compliance-working-card.md | Applied (removed from monitor tier; new "Appetite-control / appetite-suppressant positioning" hard-stop subsection) | PASS |
| 1.3 banned term in monitor tier + Ozempic audience-context | wiki/shameless/creative-strategy/platforms/shameless-ad-copy-patterns.md | Applied | PASS |
| 1.4 appetite-suppressant permission | wiki/shameless/creative-strategy/creative-angles.md | Applied | PASS |
| 1.5 appetite-suppressant translation row | wiki/shameless/performance/script-leaderboard.md | Applied | PASS |
| 1.6 appetite-suppressant permission | wiki/shameless/positioning/fiber-first-positioning.md | Applied | PASS |
| 1.7 banned term in "permitted now" line | wiki/shameless/creative-strategy/production/shameless-script-audit-checklist.md | Applied | PASS |
| 1.8 banned phrase in worked example | wiki/shameless/creative-strategy/fundamentals/shameless-direct-response-creative.md | Applied | PASS |
| 1.9 appetite-curbing fiber + artificial-colors claim | wiki/shameless/creative-strategy/production/shameless-shoot-guide-template.md | Applied (2 edits: body line + spec-table row) | PASS |
| 1.10 invites Made-in-USA claim | wiki/shameless/audience/objection-library.md | Applied | PASS |
| 1.11 drug-named hook + 2nd-person medication framing | wiki/shameless/positioning/glp1-dosing-companion.md | Applied (2 edits: hook line 65 + dosing blockquote line 38) | PASS |
| 1.12 historical plan doc banned monitor tier | docs/superpowers/plans/2026-04-20-shameless-static-copywriter.md | Applied (dated correction note added at top; history not rewritten, per sweep) | PASS |
| 2.1 calorie rule bans allowed 70–90 range | wiki/shameless/working-cards/brand-fact-rules.md | Applied (2 edits: stat table row + Calorie rule bullets) | PASS |
| 2.2 calories row + sweetener row | wiki/shameless/brand/product-facts.md | Applied (2 edits) | PASS |
| 2.3 calories row | wiki/shameless/creative-strategy/platforms/shameless-ad-copy-patterns.md | Applied | PASS |
| 2.4 mislabels "90 calories" as stat slip | wiki/shameless/creative-strategy/top-performer-patterns-observed.md | Applied | PASS |
| 2.5 offer phrasings missing sub-gate | pricing-and-offers.md; working-cards/brand-fact-rules.md; platforms/shameless-ad-copy-patterns.md | Applied (3 files; the shameless-ad-copy-patterns offer row) | PASS |

**Skipped (per task instruction — tone tier):** 3.1 (verbatim creator misstatements uncorrected), 3.2 (reformulation direction named as allulose), 3.3 (compliance-working-card over-bans "GLP-1" category term). Not applied.

## Notes / deviations
- Every finding was located at (or within a couple lines of) the line number quoted in the sweep. No file had moved or been re-edited since the sweep; no finding required re-location or skipping for staleness.
- Replacement text applied verbatim as specified in the sweep, including its em dashes and the `70–90` en-dash forms. The task's "apply each replacement exactly as specified" instruction was treated as overriding RULES rule 5's em-dash ban for these internal compliance-reference cards (the surrounding wiki prose already uses em dashes throughout).
- Did NOT touch `wiki/index.md` or `wiki/log.md`. No new pages were created (all edits in-place), and the sweep explicitly flags `log.md` as append-only history not to be rewritten. Kept strictly to the sweep's fix list per task scope.
- Sweep "Open questions" (items 1–3: the out-of-wiki `shameless-static-copywriter/knowledge/` pack, `raw/brand-context/compliance_guide.md`, `~/systems/compliance-eval/policy.json`) are out of this task's scope and left untouched. Flagged here for follow-up.
