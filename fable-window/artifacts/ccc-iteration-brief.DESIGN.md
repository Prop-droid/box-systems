# CCC Iteration-Brief Pipeline - Design (decision-ready)

Task 47, fable-window 2026-07-06. Design only, no code. Author: opus-4-8 headless.

Goal: turn a proven winner (ClickUp source id + BQ performance + the 10-type
video-iteration taxonomy) into a ready-to-push ClickUp iteration brief that names
the RIGHT iteration type for the diagnostic, holds the winning copy, states the
metric to beat, and routes to the right owner. This is the "brief CREATION system"
NEXT FOCUS from `project_ccc_research_lanes` step (1), now specified end to end.

Source-of-truth memories: `project_clickup_video_iteration_system` (10-type taxonomy),
`project_ccc_research_lanes` (current ITERATE brief state, GAPS, OPEN FORK),
`project_compliance_eval_harness` (the eval-gate lesson), `clickup-task-creator` skill
(field/naming canon), task-40 `ccc-dev-map.SUMMARY.md` (branch states).

---

## 1. Where we are today (grounded in code, not memory)

There are two brief engines that do not share a standard:

- **(A) Deterministic template** `lib/clickup.ts` `buildBriefPayload` + `actionFraming`
  drives ITERATE / BRIEF / SCALE / KILL / SWITCH_LP. The 2026-06-29 "richer-deterministic"
  pass already made ITERATE good: it emits `🟧 OUTPUT`, `🟩 WHY IT WON` (real BQ perf line),
  `🟦 INSTRUCTIONS` with a generic one-variable axis line, an embedded `🖼️ REFERENCE`
  image (or video play-link), and `🟥 Copywriting (locked)` with the real winner headline
  and hook. It inherits the source task name (`inheritedTaskName`) and source custom fields
  (`fetchSourceTask` + `inheritedFieldPatches`).
- **(B) LLM brief-job** `lib/briefJob.ts` `buildBriefPrompt` -> detached `claude -p`
  (`scripts/run-brief-job.sh`). Richer, but built ONLY for the idea -> image-test path.

**What ITERATE still does NOT do (the actual gap this design closes):**

1. It is **taxonomy-blind.** The instruction is a generic "change exactly ONE variable:
   hook, visual, layout, format, or ICP." It never picks WHICH of the 10 iteration types
   fits the winner's failure/opportunity diagnostic. The whole point of the taxonomy
   (`project_clickup_video_iteration_system`) is that the diagnostic dictates the type.
2. It is **video-blind.** `buildCustomFields` hardcodes Deliverable = Product Image and
   OUTPUT = "10 images" even when the winner is a VIDEO. A HOOK_SWAP on a video winner is a
   video edit, not 10 static images. (Flagged in `project_ccc_research_lanes` as an open gap.)
3. It has **no metric-to-beat.** WHY IT WON prints the winner's numbers, but the brief never
   states the explicit bar the iteration must clear (e.g. "beat 2.1 cmROAS / 28% hold").
4. **Responsible routing is single-lane.** Everything goes to the one Designer group; a video
   edit vs a static test vs an AI-variant should route to different owners.
5. **No net-new lane discipline.** The taxonomy is 70/30 net-new canon; nothing in CCC
   enforces or even surfaces the iterate-vs-new-concept decision at brief time.

So this is an **extension of engine (A)**, not a new engine. The ITERATE plumbing (name
inheritance, field inheritance, reference embed, locked copy, dry-run gate) is reused
verbatim. We add a **type-selection layer** in front of it and a **type -> deliverable/
routing/output map** behind it.

---

## 2. Data inputs

| Input | Source | Already in CCC? | Use |
|---|---|---|---|
| Source winner ClickUp id (SH-####) | WinnersView row / CreativeDetail | yes (`d.creative`) | name + field inheritance via `fetchSourceTask` |
| BQ performance (spend, cmROAS, ROAS, contribution, orders, hook, hold) | `winnersSql` -> `/api/winners` -> `WinnerContext` | yes (`context` prop) | WHY IT WON + diagnostic + metric-to-beat |
| Asset type + asset/post link + headline/first_sentence | `winnersSql` (`ai_headline`, `ai_first_sentence`, asset cols) | yes (`WinnerContext`) | reference embed, locked copy, video-vs-static branch |
| **Diagnostic signals** (CTR, CVR/purchase-rate, frequency, days-live, trend) | BQ - **partially missing from `WinnerContext` today** | **NO - add** | drives type selection (see 4) |
| **10-type taxonomy + type metadata** (deliverable, output shape, Responsible, P.D.A. axis, trigger diagnostic) | canon `video-iteration-formats.md` (Code Things wiki) | **NO - not on box** | the type -> brief mapping table |
| Winner-archive graduation weights (which iteration types actually became performers) | `winners.jsonl` | JSONL fill-only | rank tie-broken type suggestions (full version only) |

**Two data facts to lock before building:**

- The diagnostic needs **CTR, purchase/landing-conversion, frequency, days-live, and a
  short-window trend** on top of the metrics already in `WinnerContext`. `winnersSql` in
  `lib/queries.ts` must select them; `WinnerContext` gains `ctr`, `cvr`, `frequency`,
  `daysLive`, `cmRoasTrend` (all optional, degrade-safe like the existing fields).
- The **type metadata is canon that does not live on this box.** `video-iteration-formats.md`
  (the "proposed 10-type ClickUp task taxonomy" + diagnostic->iteration map + P.D.A. axis +
  Responsible-per-type) exists in the Mac Code Things wiki; it is NOT synced to the agent box
  (`find ~/brain ... video-iteration-format*` returns nothing). So the type metadata must be
  captured as a **committed data file in the repo** (`lib/fixtures/iteration-taxonomy.json`),
  authored once from the canon, versioned, and eval-tested. This is also the CCC pattern
  (every new data shape gets a pure parser + a committed fixture + a vitest, per repo CLAUDE.md).

---

## 3. Where it lives in CCC

**Branch: `feat/brain-tab`** (the checked-out, live, superset branch per task 40). It already
carries the entire richer-deterministic ITERATE work this extends. Do NOT branch off main
(main has the OLD thin ITERATE brief) and do NOT use `iterate-button-image` (parked, divergent
full-posting variant, +9/-24 vs main - a dead end; its posting logic was superseded by the
`/api/actions/brief` + `createTask` flow already on `feat/brain-tab`). Build here so the feature
rides along when `feat/brain-tab` finally merges to main.

Files (new + touched):

```
lib/iterationTaxonomy.ts        NEW  pure: load+validate taxonomy JSON, type metadata lookups
lib/fixtures/iteration-taxonomy.json  NEW  the 10 types + metadata (authored from canon)
lib/iterationDiagnostic.ts      NEW  pure: BQ metrics -> ranked iteration-type recommendation(s)
lib/clickup.ts                  EDIT extend Decision with iterationType; type-aware actionFraming,
                                     buildCustomFields (deliverable/output/Responsible per type)
lib/queries.ts                  EDIT winnersSql selects ctr/cvr/frequency/days-live/trend
app/api/winners/route.ts        EDIT carry new metrics into WinnerContext
app/api/actions/iterate/route.ts NEW (or extend brief route) accept iterationType, gate LLM step
app/components/IterationBriefModal.tsx NEW human-in-loop confirm UI (type picker + preview)
app/components/WinnersView.tsx / CreativeDetail.tsx  EDIT open the modal instead of firing blind
tests/iterationDiagnostic.test.ts, tests/iterationTaxonomy.test.ts  NEW vitest
```

UI trigger stays where it is: WinnersView `ActionButton action="ITERATE"` and CreativeDetail
(verdict -> ITERATE). The change is that the button opens the **IterationBriefModal** (preview +
confirm) rather than POSTing a blind brief.

---

## 4. The core new piece: diagnostic -> iteration type

This is the intelligence the taxonomy memory calls for ("diagnostic->iteration map"). It is a
**deterministic scorer**, NOT an LLM call. Input = the winner's BQ metrics; output = a ranked
list of iteration types with a one-line reason each. Modeled on `compliance-eval`'s "deterministic
core, data-driven rules" shape so it is testable and does not drift.

Rule sketch (exact thresholds are data in `iteration-taxonomy.json`, tuned against the archive):

| Diagnostic signal | Reading | Recommended type(s) |
|---|---|---|
| Low hook rate (video) | weak thumb-stop | HOOK_SWAP, INTRO_SWAP |
| Good hook, low hold | mid-video drop-off | BODY_EDIT, BODY_FORMAT, LENGTH_VARIANT |
| Good hold, low CTR/CVR | watches but doesn't click/buy | CTA_VARIANT, SOCIAL_PROOF_INSERT, FORMAT_SWAP |
| Proven winner, rising frequency + declining cmROAS | fatigue | CREATOR_SWAP, AI_VARIANT, FORMAT_SWAP |
| Static winner, strong cmROAS, wants scale | format expansion | FORMAT_SWAP (static->video), AI_VARIANT |
| Winner too different to iterate cleanly | out of scope | NET_NEW_CONCEPT lane (do not force an iteration) |

Design rules:

- **One variable, one type.** The selector returns a single primary type per brief (each brief =
  one clean variable, taxonomy canon). It may list runner-up types in the preview so the human can
  override, but a brief commits to exactly one.
- **Static winners cannot get video-only types.** HOOK_SWAP/INTRO_SWAP/LENGTH_VARIANT/CREATOR_SWAP
  are gated on `assetType === VIDEO`; a static winner is limited to its valid subset
  (SOCIAL_PROOF_INSERT, CTA_VARIANT, FORMAT_SWAP, AI_VARIANT, BODY_FORMAT). The taxonomy JSON marks
  each type `appliesTo: [VIDEO|IMAGE|BOTH]`.
- **Metric-to-beat is computed here.** The bar = the source winner's own primary metric at the
  stage the iteration targets (beat its hook rate for a HOOK_SWAP, beat its cmROAS for a
  CTA/format test). Printed explicitly in the brief.
- **Missing signals degrade, they don't crash.** If CTR/frequency are absent, the selector falls
  back to hook/hold only, and if those are absent (static, no video metrics) it defaults to
  FORMAT_SWAP or SOCIAL_PROOF_INSERT and flags "low-confidence: pick manually" in the preview.

Output shape (returned to the modal and threaded into `Decision`):

```
{ type: 'HOOK_SWAP', confidence: 'high'|'low',
  reason: 'Hook 18% vs 30% account median - thumb-stop is the bottleneck',
  metricToBeat: '30% hook rate', runnersUp: ['INTRO_SWAP'] }
```

---

## 5. Generation flow: deterministic vs LLM, and the eval gate

**The decision: deterministic scaffold, LLM strictly optional and eval-gated.**

The load-bearing lesson from `project_compliance_eval_harness`: ~49% of un-gated LLM
"optimizations" score BELOW baseline. Any LLM output in a pipeline that auto-pushes to a
shared surface (ClickUp, a real editor's queue) must be gated on a hard, deterministic,
external metric, or it drifts. So the flow is tiered:

**Tier 0 - deterministic (MVP, ships first).** No LLM at all.
- Selector picks the type (section 4).
- The type's metadata (from `iteration-taxonomy.json`) fills the brief: OUTPUT shape,
  the specific "hold X / vary Y" instruction line for that type, deliverable type, Responsible.
- WHY IT WON + metric-to-beat from BQ.
- Copy stays LOCKED (the existing `copyBlock`) - for a retro the copy does not change, so
  there is NOTHING for an LLM to write. This is why the richer-deterministic path was chosen
  for ITERATE in the first place (per `project_ccc_research_lanes`), and it holds here.

This tier is a **complete, correct, decision-ready brief.** It needs no model call.

**Tier 1 - narrow LLM "iteration directions" (full version, opt-in, eval-gated).** The ONE
place an LLM adds value: turning "type = HOOK_SWAP, hold the offer" into 3-5 concrete,
on-canon hook directions the editor can execute ("open on the 9pm-cravings beat instead of the
stat-shock"). This is generative and worth a model, but it is exactly the drift-prone step the
eval lesson warns about. Therefore:

- It runs through the detached-job pattern (`briefJob.ts` style) OR inline `claude -p`, but its
  output is **scored before it reaches ClickUp** by a new `iteration-brief-eval` harness built on
  the `compliance-eval` template (the eval-factory template in artifacts already generalizes this):
  - HARD checks (regression = block): compliance-clean (reuse Shameless `policy.json`),
    no em dashes, **one-variable discipline** (the directions must not propose changing more than
    the selected type's axis - e.g. a HOOK_SWAP direction that also rewrites the CTA fails),
    **copy-lock respect** (must not rewrite the winning locked headline/hook), structure
    (direction count within 3-5).
  - On regression: fall back to Tier 0 (ship the deterministic brief without LLM directions)
    and note it. Never push an ungated LLM brief.
- The harness is fixture-gated first (`test_scorer.py` at precision=recall=1.0 before trusting
  it), same discipline as compliance-eval and the email-eval instance already in artifacts.

Net: **the pipeline is correct and shippable with zero LLM. The LLM is a quality add-on that
can only ever improve on, never replace or corrupt, the deterministic brief, because it is
gated.** That is the eval-gate lesson applied.

---

## 6. Human-in-loop points

Auto-push-to-ClickUp with no human check is the wrong default for a shared work queue. The
loop:

1. **Type confirmation (primary gate).** Clicking ITERATE opens `IterationBriefModal`:
   shows the recommended type + reason + metric-to-beat, the runner-up types as one-click
   overrides, and a live preview of the rendered brief (name, blocks, deliverable, Responsible).
   Human confirms or switches type. Low-confidence selections open with no type pre-committed.
2. **Net-new escape hatch.** The modal surfaces "this looks like a NET_NEW_CONCEPT, not an
   iteration" when the selector returns that, and offers to route to the idea-brief flow
   instead. Keeps the 70/30 canon visible at the decision point.
3. **Dry-run preview by default.** Reuse the existing `CLICKUP_DRY_RUN` / `writeEnabled()` gate.
   The modal's "Preview" shows the exact payload; "Push" performs the write only when
   `CLICKUP_WRITE_ENABLED=1`. Same safety model already in `lib/clickup.ts`.
4. **Post-push confirmation.** Return the task URL (URL-handoff pattern) so Tomas taps one link
   to verify name/image/fields, matching how every other CCC brief closes.

For the twice-weekly headless drop (`project_iteration_suggestions_drop`) the same selector
feeds suggestions, but that path is already human-in-loop by construction (it posts SUGGESTIONS
to chat with task links, a human briefs from them) - no change needed, though the two should
share the selector so the chat drop and the CCC button never disagree on type.

---

## 7. ClickUp push (task-creator conventions)

Reuses the locked 3-block template and `createTask` verbatim; the taxonomy adds a per-type
overlay. Everything below is data in `iteration-taxonomy.json`, keyed by type:

- **Deliverable Type** (fixes the video-blind bug): video types (HOOK_SWAP, INTRO_SWAP,
  BODY_EDIT, LENGTH_VARIANT, CREATOR_SWAP, FORMAT_SWAP->video, AI_VARIANT) -> a VIDEO deliverable
  option id; static types -> Product Image (current default). The current hardcoded
  `deliverableProductImage` becomes a per-type lookup. **ACTION: the VIDEO deliverable option
  id(s) must be pulled from the live list** - not in the code today (only Product Image is).
- **OUTPUT line**: video types -> "N video variations" (not "10 images"); static -> "10 images".
- **Responsible routing**: per-type owner group/user (video editor vs static designer vs
  AI-variant owner). Current single `designerGroup` becomes a per-type field in the taxonomy JSON.
  Falls back to `designerGroup` for any type without an explicit owner so it never posts unrouted.
- **Project Type = Retro** (already correct for ITERATE via `projectTypeRetro`).
- **Naming**: keep `inheritedTaskName` but the marker becomes type-aware, e.g. `retro_HookSwap`
  instead of bare `retro`, so the queue is legible (`SHA_2026_S27_..._retro_HookSwap_Tom`).
  This is a one-token change to the existing marker logic.
- **Field inheritance** (Product, Brand, PM, Responsible-base, FB Ad3 LP, FB Ad6/7 copy):
  unchanged, via `fetchSourceTask` + `inheritedFieldPatches`. Landing Page Link still NOT
  inherited (per Tomas 2026-06-29).
- **Reference embed + locked copy**: unchanged (`referenceBlock` + `copyBlock`), including the
  FB-hotlink re-host on real writes (download asset, attach, swap embed to ClickUp url).
- **Description adds**: `🎯 METRIC TO BEAT: <bar>` block and a `🔁 ITERATION TYPE: <type> - <the
  type's hold/vary rule>` line replacing today's generic one-variable sentence.

All field UUIDs, option ids, people/group ids already live in `TPL` in `lib/clickup.ts`; the
only NEW ids needed are the VIDEO deliverable option id and any per-type Responsible group ids.

---

## 8. MVP cut vs full version

**MVP (Tier 0, deterministic, no new model calls). Ships on `feat/brain-tab`.**
1. `iteration-taxonomy.json` authored from the canon (10 types: appliesTo, deliverable, output,
   Responsible, hold/vary rule, trigger diagnostic) + `lib/iterationTaxonomy.ts` loader + vitest.
2. `lib/iterationDiagnostic.ts` selector (section 4) + vitest against fixtures.
3. `winnersSql` + `WinnerContext` gain ctr/cvr/frequency/days-live/trend.
4. `Decision.iterationType`; type-aware OUTPUT / deliverable / Responsible / metric-to-beat /
   type-specific instruction line in `buildBriefPayload` + `buildCustomFields`.
5. `IterationBriefModal` with type confirm + override + dry-run preview + push.
6. Verify: `scripts/verify.sh` green + one live dry-run against the running server (a real
   ITERATE preview for a video winner and a static winner).

Delivers: correct type selection, video-correct deliverables (kills the "10 images for a video"
bug), explicit metric-to-beat, per-type routing, human confirm. No LLM, no drift risk.

**Full version (adds on top of MVP, each independently shippable):**
- Tier 1 LLM iteration-directions, behind the `iteration-brief-eval` gate (section 5).
- Archive-weighted type ranking: bias the selector toward iteration types that historically
  graduated to performers for SHA (`winners.jsonl`), as a tie-breaker only.
- Batch mode: select-and-brief the top N winners from WinnersView in one pass (feeds / mirrors
  the twice-weekly chat drop).
- Shared selector wired into `project_iteration_suggestions_drop` so chat suggestions and the
  CCC button agree on type.
- Net-new detector maturity: promote the "looks like NET_NEW" heuristic into a real
  iterate-vs-new-concept score.

---

## 9. Rollout accounting for the branch states (task 40)

- Build on **`feat/brain-tab`** (checked out = live). New files + surgical edits to
  `lib/clickup.ts` / `lib/queries.ts` / winners route. Per repo CLAUDE.md, dev-mode hot-reloads;
  no `npm run build` against the live `.next`.
- `feat/research-lanes` is fully absorbed by `feat/brain-tab` (redundant) - ignore.
- Do NOT resurrect `iterate-button-image` (parked, divergent posting logic superseded here).
- The box has no GitHub creds; the eventual merge of `feat/brain-tab` -> main (and this feature
  with it) needs the Mac. Nothing here changes that; it just adds to the same unmerged superset.
- Guardrail: `.env.local` is runtime-required and `lib/config.ts` defaults are Mac-era. Green
  `verify.sh` does not prove the ClickUp push works - the live dry-run (step 6) is mandatory
  before claiming done, per the VERIFY discipline task 40 recorded.

---

## 10. Open questions / decisions Tomas needs to make

1. **Author the taxonomy JSON from canon.** `video-iteration-formats.md` is NOT on the agent box.
   Someone with the Mac wiki (or a re-sync) must supply the per-type metadata (deliverable option
   id, Responsible owner, hold/vary rule, trigger thresholds, P.D.A. axis) so
   `iteration-taxonomy.json` is authored from truth, not guessed. Everything else is buildable now;
   this is the one hard dependency.
2. **VIDEO deliverable option id(s)** and any **per-type Responsible group ids** must be pulled
   from the live Creative Strategist list - only Product Image + the single Designer group are in
   the code today.
3. **Retro == iteration?** `project_ccc_research_lanes` left this unresolved (is "retro" the same
   as an iteration, or a distinct sprint-wrap task). The current code treats ITERATE = retro. This
   design assumes that holds; confirm before renaming markers per-type.
4. **LLM directions - worth it?** Tier 0 is a complete brief with copy locked. Tier 1 only adds
   suggested hook/body DIRECTIONS. Decide whether that quality add is worth building + maintaining
   an eval harness for, or whether the deterministic brief plus the editor's own judgment is enough.
5. **Auto-push vs draft.** This design defaults to human-confirm + dry-run preview. Confirm that is
   the wanted posture (vs the button pushing directly on click like the current ITERATE flow does).

---

## Appendix A - data-flow (MVP)

```
WinnersView / CreativeDetail row
  -> WinnerContext (BQ: spend/cmROAS/ROAS/contrib/orders/hook/hold + NEW ctr/cvr/freq/daysLive/trend,
                    assetType/assetLink/postLink, headline/firstSentence, sourceName)
  -> [click ITERATE] -> iterationDiagnostic.select(context, taxonomy)
       -> { type, confidence, reason, metricToBeat, runnersUp }
  -> IterationBriefModal (human confirms / overrides type; dry-run preview)
  -> POST /api/actions/iterate { creative: SH-####, iterationType, context, note }
  -> lib/clickup.ts buildCreateBody(Decision{action:ITERATE, iterationType, context})
       - name: inheritedTaskName(..., marker=`retro_<Type>`)
       - blocks: OUTPUT(type) + WHY IT WON + METRIC TO BEAT + ITERATION TYPE rule
                 + INSTRUCTIONS + REFERENCE(embed) + Copywriting(locked)
       - fields: inherited (fetchSourceTask) + Deliverable(type) + Responsible(type) + Project Type=Retro
  -> createTask (CLICKUP_WRITE_ENABLED gate; asset re-host; user/group field PATCH)
  -> TASK_URL back to UI (one-tap verify)
```

## Appendix B - the 10 types (from `project_clickup_video_iteration_system`)

HOOK_SWAP, INTRO_SWAP, BODY_EDIT, SOCIAL_PROOF_INSERT, BODY_FORMAT, CTA_VARIANT,
CREATOR_SWAP, LENGTH_VARIANT, FORMAT_SWAP, AI_VARIANT, plus the NET_NEW_CONCEPT lane
(iterate-vs-new-concept escape). Each row of `iteration-taxonomy.json` carries:
`appliesTo` (VIDEO/IMAGE/BOTH), `triggerDiagnostic`, `holdVaryRule`, `deliverableOptionId`,
`outputLine`, `responsible`, `pdaAxis`, `nameMarker`. Authored from the canon page (dep #1).
