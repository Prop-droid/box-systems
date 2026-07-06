# Diagnosis: all 12 research lanes have suggestedBrief = null

Date: 2026-07-06. Diagnosis only, nothing applied. Blocks the Monday Brief Conveyor idea
(the "Brief this lane" button is the conveyor's entry point and it never renders on live data).

## Verdict

**Unshipped optional scope, not a regression.** The field was born null and no code has
ever populated it. Spec step 5 ("Suggest, Gemini pass 3") was explicitly marked *optional*,
the implementation plan contains no task for it, and the plan's own code listing hardcodes
`suggestedBrief: null`. Every layer downstream of the generator (parser, API, UI) handles
the field correctly; the UI simply hides the brief affordance when it is null, which on
live data is always.

**Second finding (matters for the fix):** even if pass 3 were implemented exactly per spec
(gap/emerging lanes only), it would fill **zero** briefs today. The 2026-07-05 snapshot
classifies the 12 lanes as 3 proven-ours / 8 watching / 1 fading, with no gap or emerging.
The relative classifier (`classifyLanes`, added in `ee932fa`) only emits `gap` for
strong-validation lanes that are *uncovered*, and 9 of 12 lanes are covered. Any patch
must widen the actionable set or the conveyor stays empty anyway.

## Data path trace (where it dies)

1. **Generator, root cause** `~/systems/research-agent/lanes/score.mjs:64`
   `assembleLane()` returns `... momentum: mom, evidence, suggestedBrief: null,` for every lane.
2. **Generator orchestrator** `~/systems/research-agent/lanes/build-lanes.mjs:149-162`
   maps canon through `assembleLane`, re-classifies via `classifyLanes`, and writes the
   result straight to `latest.json`. Nothing touches `suggestedBrief` in between.
   `tag.mjs` has only pass 1 (`tagAds`) and pass 2 (`proposeLanes`); no suggest function exists.
3. **Live data** `~/brain/systems/research-agent/output/lanes/latest.json`
   (generatedAt 2026-07-05T22:07Z, nightly via `research-deepdive.timer` -> `run-lanes.sh`):
   all 12 lanes `suggestedBrief: null`. Confirmed by jq.
4. **CCC parser** `lib/lanes.ts:19` types the field `string | null` and passes it through. OK.
5. **CCC API** `/api/research/lanes` serves the parsed file. OK.
6. **CCC UI** `app/components/research/LanesView.tsx:113,251` renders the brief text and the
   "Brief this lane" button only when `lane.suggestedBrief` is truthy, and posts
   `{ action: 'BRIEF', creative: lane.label, note: lane.suggestedBrief }` to
   `/api/actions/brief`. Correct behavior; permanently hidden on live data.
7. **Fixture** `lib/fixtures/lanes-latest.sample.json:13` has a populated example, which is
   why the feature looks finished in dev/fallback and in the plan's manual verification.

## Evidence

- `~/systems` git: `git log -S suggestedBrief` shows only the creating commits. Commit
  `6b43022` (2026-06-25, "feat(lanes-engine): pure scoring...") introduced `score.mjs`
  already containing `suggestedBrief: null` at line 64. Later commits (`2e9ef7b` tests,
  `ee932fa` relative classification) never changed it. Never populated, never regressed.
- Spec `docs/superpowers/specs/2026-06-25-research-lanes-redesign.md:154`:
  "5. **Suggest (Gemini pass 3, optional)** — a one-line `suggestedBrief` per actionable
  (gap / emerging) lane." Only pipeline step labeled optional.
- Plan `docs/superpowers/plans/2026-06-25-research-lanes-redesign.md`: no C-task implements
  pass 3; the Task C1 code listing (line 584) itself hardcodes `suggestedBrief: null`.
  Wrinkle: the plan's manual verification step (line 902) expects "a `gap` lane shows
  Test-now + a suggested brief", satisfiable only by the fixture. So the gap was visible
  at plan time and glossed by fixture data.
- Generator contract test `score.test.mjs:64` asserts only that the *key* exists, not a value.
- Live classification spread (jq over latest.json): gap 0, emerging 0, proven-ours 3,
  watching 8, fading 1. Only 2 lanes have strong competitor validation
  (gut-health-regularity, candy-without-guilt); 3 have momentum up.

## Proposed patch (NOT applied)

Two files, both in `~/systems` (repo `Prop-droid/box-systems`, branch `main`, its only
branch). **Zero CCC changes needed**; parser, API, tests, and UI already support the field.
Full replacement files per RULES rule 3: `artifacts/ccc-lanes-bug/tag.mjs` and
`artifacts/ccc-lanes-bug/build-lanes.mjs` (both `node --check` clean; `suggestBriefs`
smoke-tested with injected fetch: fills actionable lanes only, `{}` on Gemini error).

Design calls:
- Suggestion happens in the orchestrator *after* `classifyLanes` (actionability depends on
  final classification), so `score.mjs` stays pure and untouched.
- Actionable set = spec's gap/emerging **plus** watching lanes with strong validation or
  momentum up. Rationale: second finding above; per-spec targeting fills 0 briefs today.
  On the current snapshot this yields 5 lanes (gut-health-regularity, candy-without-guilt,
  keto-low-net-carb*, fiber-deficit*, and none of the weak/down watchers; *proven-ours
  excluded, momentum-up watchers included). Tune the predicate in one place
  (`actionableForSuggest`) if Tomas wants briefs on proven-ours too.
- Same failure discipline as passes 1-2: never throws, logs and returns `{}`, so a Gemini
  outage leaves briefs null instead of killing the nightly run.

### Diff 1: `~/systems/research-agent/lanes/tag.mjs` (append after `proposeLanes`)

```diff
@@ -85,3 +85,50 @@ export async function proposeLanes(unmatchedAds, key, fetchImpl = fetch) {
     console.error('proposeLanes failed:', e.message)
     return []
   }
 }
+
+// Lanes worth a one-line brief suggestion (Gemini pass 3). Spec says gap/emerging;
+// watching lanes with strong competitor validation or upward momentum are included
+// because the current classifier (relative, account-tier) rarely emits gap/emerging
+// (2026-07-05 snapshot: 0 of 12), which would leave pass 3 a no-op.
+export function actionableForSuggest(lane) {
+  if (lane.classification === 'gap' || lane.classification === 'emerging') return true
+  return (
+    lane.classification === 'watching' &&
+    (lane.competitorValidation.score === 'strong' || lane.momentum === 'up')
+  )
+}
+
+/**
+ * Suggest a one-line test brief per actionable lane (Gemini pass 3, spec step 5).
+ * Never throws; errors return {} so suggestedBrief stays null for that run.
+ * @param {Array} lanes - scored+classified Lane objects
+ * @param {string} key - Gemini API key
+ * @param {Function} fetchImpl - Injected fetch
+ * @returns {Promise<Record<string, string>>} Map of laneId -> one-line brief
+ */
+export async function suggestBriefs(lanes, key, fetchImpl = fetch) {
+  const actionable = lanes.filter(actionableForSuggest)
+  if (!actionable.length) return {}
+  const list = actionable
+    .map(l => {
+      const ev = l.evidence?.[0]
+      return (
+        `- ${l.id}: ${l.label} [${l.classification}; ${l.competitorValidation.advertisers} advertisers / ${l.competitorValidation.variants} variants; momentum ${l.momentum}]` +
+        (ev ? ` e.g. ${ev.brand}: "${(ev.title || '').slice(0, 80)}"` : '')
+      )
+    })
+    .join('\n')
+  const prompt =
+    `You write one-line creative test briefs for Shameless Snacks (high-fiber, low-sugar gummy candy; 26g fiber, 70 cal, 3g sugar). For each lane below, write ONE sentence in the shape "test <specific angle> for <specific persona>", grounded in the lane's evidence. No health claims beyond fiber/digestion. Return STRICT JSON {"<laneId>":"<one line>"}. No prose.\nLANES:\n${list}`
+  try {
+    const map = await geminiJSON(key, prompt, fetchImpl)
+    const out = {}
+    for (const l of actionable) {
+      if (typeof map[l.id] === 'string' && map[l.id].trim()) out[l.id] = map[l.id].trim()
+    }
+    return out
+  } catch (e) {
+    console.error('suggestBriefs failed:', e.message)
+    return {}
+  }
+}
```

### Diff 2: `~/systems/research-agent/lanes/build-lanes.mjs`

```diff
@@ -4,7 +4,7 @@ import { readdirSync, readFileSync, existsSync } from 'fs'
 import { join } from 'path'
 import { execFileSync } from 'child_process'
 import { assembleLane, classifyLanes } from './score.mjs'
-import { tagAds, proposeLanes } from './tag.mjs'
+import { tagAds, proposeLanes, suggestBriefs } from './tag.mjs'
@@ -151,6 +151,11 @@ async function main() {
   // Final classification is RELATIVE across our covered lanes (see classifyLanes).
   lanes = classifyLanes(lanes)

+  // Gemini pass 3 (spec step 5): one-line suggestedBrief per actionable lane.
+  // Runs after classifyLanes because actionability depends on final classification.
+  const briefs = await suggestBriefs(lanes, KEY)
+  lanes = lanes.map(l => ({ ...l, suggestedBrief: briefs[l.id] ?? null }))
+
   const unmatched = recent.filter(a => adLaneRaw[a.id] === 'unmatched')
   const proposed = await proposeLanes(unmatched, KEY)
@@ -172,7 +177,7 @@ async function main() {
   console.log(
-    `lanes: ${lanes.length} scored, ${proposed.length} proposed, ${Object.keys(adLane).length} ads tagged`,
+    `lanes: ${lanes.length} scored, ${proposed.length} proposed, ${Object.keys(briefs).length} briefs suggested, ${Object.keys(adLane).length} ads tagged`,
   )
 }
```

### CHANGES

- `tag.mjs`: purely additive. New exports `actionableForSuggest` (predicate, unit-testable)
  and `suggestBriefs` (pass 3, batched in one call for <=12 lanes, JSON mode, temperature 0,
  error-swallowing like the other passes). Why: implements spec step 5, the missing producer.
- `build-lanes.mjs`: one import, 4 lines after `classifyLanes`, updated summary log line.
  Why: wire pass 3 into the nightly run and make brief counts observable in journal logs.

## Effort estimate

**~1 to 1.5 hours** on the generator side: apply both diffs, add a `node --test` case for
`actionableForSuggest` + `suggestBriefs` with injected fetch (mirroring `tag.test.mjs`),
run `GEMINI_API_KEY=... node build-lanes.mjs --dry-run` and eyeball the 5 suggested lines
for compliance (no banned claims), then let the nightly timer ship it. Zero CCC work; the
Lanes UI picks it up on next fetch. Add ~30 min if Tomas wants the predicate driven from
canon.json (per-lane opt-in) instead of code.

## Which branch

- **Generator fix**: `~/systems` repo, `main` (single-branch repo, canonical home of the
  lanes engine per box conventions). Commit style there: `feat(lanes-engine): ...`.
- **CCC**: no code change. Note the consuming UI (`LanesView.tsx`, `lib/lanes.ts`) exists
  only on `feat/brain-tab` (and its redundant subset `feat/research-lanes`), not on `main`;
  since `feat/brain-tab` is the live checkout, the fix is visible immediately, but merging
  `feat/brain-tab -> main` remains a prerequisite for the conveyor to survive a checkout
  of main. Also update the CCC `CLAUDE.md` "Known bugs" entry when the fix lands.

## Open questions for Tomas

1. Actionable-set widening (watching + strong-or-up) is my call, not the spec's. OK, or
   spec-strict gap/emerging only (accepting 0 briefs on current data), or all non-fading?
2. Should proven-ours lanes get iteration briefs too (currently excluded; the Iterate tab
   partly covers that path)?
3. Alternative resolution: drop the field and build the conveyor on `actionFor(lane)`
   labels instead. Cheaper (delete ~20 UI lines), but loses the one-line angle suggestion
   the conveyor presumably wants. Not recommended.
