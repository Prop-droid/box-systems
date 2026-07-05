# CCC persona-driven UX pass - 2026-07-03

Setup: app answered on http://localhost:3000 (307 to /performance?tab=today, then 200).
Branch checked out and live: `feat/brain-tab` (e689d83, merge of iterate-recs work). feat/research-lanes is already merged into this; the lanes UI is live.
Driver: Playwright 1.61.1 headless Chromium, desktop 1440x900 + mobile 390x844.
Screenshots: ~/fable-window/artifacts/ccc-ux/ (18 page shots `desktop-*` / `mobile-*`, plus `flow-*` interaction shots, `sweep-notes.json`, `interact-notes.json`).
Read-only pass: no repo changes. One API call was made to POST /api/actions/brief with `?dryRun=true` (returned dryRun payload, no ClickUp task created).

---

## Persona walkthroughs (summary)

**P1: Tomas at 7am.** The answer IS above the fold: "Friday, July 3. This week $79K spend, cmROAS 0.61 vs 1.0 break-even, 1 scale, 28 kill, 0 watch" plus Iterate Next and Just Launched with per-ad KEEP/KILL verdicts. Content-wise this is a 9/10 morning screen. Two things break the under-10-seconds promise: cold loads (22s for Today, 49s for the tab set, because the service runs `npm run dev` and compiles routes on first hit; warm loads are 1.4-4s), and the "28 kill" number being plain text with no way to see the 28.

**P2: Tomas on the phone at 390px.** Broken. The 200px fixed sidebar never collapses, content renders in the leftover ~190px, and 8 of 9 pages scroll horizontally (Today scrollWidth 783px vs 390 viewport; Winners renders as overlapping unreadable columns, see mobile-winners-fold.png). Only /feedback happens to fit. Only the Reports page has any @media rules.

**P3: Editor with a link to one brief.** The good news: `/performance?tab=ads&sh=SH-16358` in a fresh browser (no localStorage) lands directly on that creative's card, filtered, in 2.8s, with a footer that says where data comes from. Older creative (SH-13107) also resolves. The trap: nobody would discover this URL shape without being told, there is no "copy link" affordance on cards, and the editor also sees kill verdicts and negative margins for the whole account one tab away (no scoping).

**P4: Data skeptic tracing 3 numbers.**
- Weekly report "Spend $78.7K, ROAS 0.88": PASS. Header states Source: `ejam-dwh.production.creative_dashboard`, scope caveat, and a health strip that expands to "latest data 0d old (max 3d), cogs_coverage 0.2% missing, aov band, funnel sanity" (flow-health-popover.png). Best surface in the app.
- Ad Performance grid numbers: PASS-ish. Footer: "Live snapshot from creative_dashboard. Sort / filter / search are real."
- Today digest "$79K / 0.61 / 28 kill": FAIL. No source, no as-of timestamp, no window definition ("This week" = which days of a part week?).
- Research lanes "$97.5k spend, 0.61x cmROAS" per lane: FAIL. The API carries `generatedAt: 2026-07-02T22:06` but the UI never shows it. Swipe shows "pulled 2026-07-02" (good); Lanes shows nothing.
- Bonus red flag for this persona: every lane shows "0 comment themes / 0 trend mentions" (confirmed in API: 11 of 12 lanes all-zero). Either the demand pipeline is dead or it never ran; either way the column teaches the user to distrust the screen.

**P5: First-time user.** Loading states are good (skeletons everywhere). Dead ends found: Lanes empty state says "No lanes scored yet -- run the engine" with no link or explanation of what the engine is; Feedback page greets with "Run synthesis / never run / No pending proposals" plus raw 18-digit decision IDs; Brain tab is a raw file browser exposing package-lock.json and claude-inventory.sh with zero context. None crash, but three of five nav hubs open with insider jargon.

**Research lanes / signal-to-brief end-to-end.** Partly a lie, partly a stall:
- Lane cards show an action verb top-right ("Test now", "Scale + iterate", "Sunset") that looks like a button and is a plain `<span>` (`actionFor(lane)` in LanesView.tsx:213). Clicking does nothing.
- The real CTA, "Brief this lane", only renders when `lane.suggestedBrief` exists, and it exists on 0 of 12 lanes in the live data. So from the Lanes tab there is no executable path at all.
- The rich path (GenerateBriefModal: LP picker, headline counts, headless-claude job) is orphaned code. It is only imported by OpportunityBoard, and OpportunityBoard is mounted nowhere since the 2026-06-25 redesign (research/page.tsx renders Lanes/Queue/Swipe/Comments only).
- What does work: Queue tab cards have "-> brief" with a confirm step, POSTing to /api/actions/brief. Dry-run probe succeeded end to end. But the skeleton it writes is typed as a retro image test regardless of signal: name `SHA_2026_S27_<claim>_retro_ImageTest_Tom`, description "Image test. Produce 10 image variations based on the reference creative" with no reference creative. For a lane/idea signal that task is wrong on arrival and the editor has to reverse-engineer intent.
- "View evidence" on a lane is genuinely good: deep-links to Swipe pre-filtered to the lane (12 ads, "pulled 2026-07-02").
- Adapt this (Swipe) correctly confirm-gates and writes a competitor-adapt note.

---

## Friction findings, ranked by (frequency Tomas hits it x severity)

### 1. Mobile layout is unusable at 390px
- Screen: every page except /feedback. Screenshots: mobile-performance-today-fold.png, mobile-winners-fold.png, mobile-research-fold.png.
- Expected (P2): read the morning digest from the phone over Tailscale.
- Happened: fixed 200px sidebar eats half the screen, Today digest wraps into a 190px column, Winners renders overlapping card columns that are literally unreadable, every page pans horizontally (scrollWidth up to 783px).
- Fix: in `app/globals.css` add a `@media (max-width: 900px)` block that turns `.side-nav` (line ~541, `position: fixed; width: 200px`) into a top bar or hamburger and removes the content margin; let stat rows wrap. The Reports page already has the pattern (lines 376-397), it just needs to be global. Sidebar markup: `app/components/Sidebar.tsx`.

### 2. First visit of the day can take 20-50s because the service runs `next dev`
- Screen: any, worst on /performance (49.5s cold, 1.4-4.3s warm). Evidence: sweep-notes.json loadMs vs interact-notes.json warm timings; `systemctl --user cat creative-command-center` shows `ExecStart=/usr/bin/npm run dev`.
- Expected (P1): sub-10s answer at 7am.
- Happened: every route compiles on first hit after any restart/deploy, so the "what happened overnight" screen is the one that pays the compile tax.
- Fix: build once, serve prod: `npm run build` + `ExecStart=npm run start` in the systemd unit (unit file lives with ~/systems/systemd). No code change needed.

### 3. The signal-to-brief path advertises actions it cannot perform
- Screen: Research > Lanes and Queue. Screenshots: desktop-research-fold.png, flow-research-queue.png.
- Expected (P: strategist): see a Gap lane, click "Test now", get a brief.
- Happened: "Test now" is a non-interactive span; "Brief this lane" requires `suggestedBrief` which no lane has; the full generate-brief modal is unreachable (OpportunityBoard orphaned); the Queue "-> brief" that does work writes a mislabeled `retro_ImageTest` skeleton with a nonexistent reference creative.
- Fix, in order of value: (a) mount `GenerateBriefButton` (app/components/research/GenerateBriefModal.tsx) on ActionQueue cards and/or LaneCard, replacing the skeleton-only path; (b) until the engine emits `suggestedBrief`, fall back to `lane.label` + `actionFor(lane)` so the button always renders; (c) in the brief payload builder, stop forcing action=BRIEF into the retro/ImageTest template when there is no reference creative (lib buildBriefPayload / lib/clickup.ts createTask path).

### 4. Today digest numbers are dead text with no source or freshness
- Screen: Performance > Today. Screenshot: desktop-performance-today-fold.png.
- Expected (P1 and P4): tap "28 kill" to see the 28; know what "This week" covers and when data was pulled.
- Happened: interact probe found no clickable element containing "kill"; no as-of/source line anywhere on the digest (the Ad Performance footer and Reports health strip prove the team knows how).
- Fix: make "1 scale, 28 kill, 0 watch" filter links into the verdict list below, and add the same one-line "creative_dashboard, as of <date>" footer used in CreativeGrid to `app/components/TodayScreen.tsx` / `SinceYesterday.tsx`.

### 5. Duplicate creatives render twice and spray React key warnings
- Screen: Performance > Winners and Today > Just Launched, Ad Performance grid. Screenshots: desktop-performance-today-fold.png (SH-16158 listed twice with different numbers), flow-editor-deeplink-old.png text (SH-13107-6 twice); 35 console errors "two children with the same key" on /winners (sweep-notes.json).
- Expected: one row per creative, or an explicit variant label.
- Happened: same SH code appears as two rows with different stats; a skeptic cannot tell which number is real.
- Fix: dedupe/aggregate by sh_code (or key by ad_id and label rows as variants) in `app/components/WinnersView.tsx` (WinnerCard key={w.id}, line ~472) and the winners/just-launched data mappers.

### 6. Lanes "Demand" column is all zeros
- Screen: Research > Lanes. Screenshot: desktop-research-fold.png.
- Expected (P4): demand evidence per lane.
- Happened: "0 comment themes / 0 trend mentions" on 11 of 12 lanes (API confirms zeros in the data, not a render bug), while the Comments tab shows 851 comments in 28d. The join from comments to lanes is not running.
- Fix: either wire comment-theme counts into the lane engine output, or hide the Demand block when all-zero and show "demand signal not wired yet" so the card stops looking broken. `app/components/research/LanesView.tsx` lines 240-247.

### 7. Iterate Next and ad detail lead with raw machine IDs
- Screen: Performance > Today. Screenshots: desktop-performance-today-fold.png, flow-iterate-next-click.png.
- Expected: "which ad is this?" answered by the title.
- Happened: row title is `120245108994830352`; expanded detail titles `JTNejedlo_Product_20260527_trybe=33c838c7` with "no linked task, no angle tag". The inline expansion itself is great (metrics, funnel, Brief iteration and Switch LP buttons prefilled), but the naming makes the top daily recommendation feel untrustworthy.
- Fix: prefer creative name / SH code / angle when present and demote ad_id to metadata in the Iterate row component (`app/components/IterateRows.tsx`, `TodayCard.tsx`); "no linked task" rows should link to the unmapped-spend workflow the weekly report keeps flagging ($39.4K unmapped).

### 8. Cmd+K palette offers destinations that no longer exist
- Screen: global. Screenshot: flow-cmdk.png.
- Expected: palette entries land where they say.
- Happened: "Research > Today" (?mode=today) and "Research > Opportunities" (?mode=opportunities) both silently coerce to Lanes (legacy map in app/research/page.tsx line 31), so two palette entries are duplicates of a third with misleading names.
- Fix: update the GO TO list in `app/components/CommandPalette.tsx` to the live four modes.

### 9. Cron staleness is whispered in the corner
- Screen: global sidebar footer. Screenshot: desktop-performance-today-fold.png bottom left.
- Expected (P1/P4): an obvious "research data is N days stale" cue when pipelines miss cadence.
- Happened: amber micro-text "weekly, monitor, deepdive stale" in 10px at the bottom of the sidebar, truncated on mobile, detail only on hover (tooltip). Meanwhile Lanes never shows its `generatedAt` at all.
- Fix: surface `generatedAt` as "scored <date>" on the Lanes header, and when any cron is stale show a one-line banner on the affected tab instead of only the sidebar foot (`app/components/Sidebar.tsx` CronFoot, `LanesView.tsx`).

### 10. First-run dead ends speak insider jargon
- Screen: Feedback, Brain, empty Lanes. Screenshots: desktop-feedback-fold.png, desktop-brain-fold.png.
- Expected (P5): each hub explains itself.
- Happened: "Run synthesis / never run", raw 18-digit decision IDs, "No lanes scored yet -- run the engine", Brain listing package-lock.json.
- Fix: one sentence of purpose per empty state plus the command or cron that feeds it; filter Brain's root listing to content dirs (`app/components/BrainBrowser.tsx`).

### 11. Minor: Queue cards show empty gray thumbnail boxes
- Screen: Research > Queue. Screenshot: flow-research-queue.png (top two cards).
- Happened: signal cards reserve a thumbnail slot that renders as an empty gray square when no image resolves; looks broken rather than intentional.
- Fix: drop the placeholder block when no media URL (`app/components/research/ActionQueue.tsx`).

---

## The 3 fixes that most improve daily use

1. **Make it work on the phone**: collapse `.side-nav` under 900px and let stat rows wrap (globals.css + Sidebar.tsx). Tomas checks this thing from the phone; today that is a pinch-zoom exercise.
2. **Serve a production build** (`next build` + `next start` in the user unit): turns the 7am screen from 22-50s into ~2s and removes dev-mode overhead from every cron-adjacent fetch.
3. **Close the signal-to-brief loop**: mount the orphaned GenerateBriefButton on Queue/Lane cards and stop the skeleton path from writing wrongly-typed `retro_ImageTest` tasks. This is the app's core promise (signal in, brief out) and right now the only reachable path produces a task an editor cannot execute.

Open question for Tomas: is the lane engine supposed to emit `suggestedBrief` and demand counts already (pipeline bug), or is that V2 scope (UI should stop rendering the affordances)?
