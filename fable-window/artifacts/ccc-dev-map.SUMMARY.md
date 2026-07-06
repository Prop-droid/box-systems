# CCC Dev Map — task 40 summary (2026-07-06)

Goal: make any future Claude session instantly effective in `~/creative-command-center`.
Deliverables landed IN the repo (new files only, per rule 10): `CLAUDE.md`,
`scripts/verify.sh`, `scripts/verify-baseline.txt`. Commits: `c0a1081` (empty baseline
before) → `8e6eab6` (the three new files). No existing source file touched.

## What the repo is

Next.js 14.2.35 App Router dashboard (React 18, TS 5 strict, Tailwind 3.4 + CSS-token
design system in `app/globals.css`, "airy × ledger hybrid"). Runs as systemd user service
`creative-command-center` = `npm run dev` on :3000 from this checkout — **the checked-out
branch is production**. No state library: `useApi` (TTL fetch cache + retry),
`usePersistentState` (localStorage), `WeekProvider` context.

Data flow: page → client component → `useApi('/api/...')` → `app/api/*/route.ts` →
pure logic in `lib/`. Server-only fs/BQ code is split from client-safe parsers
(`lib/lanes.ts` vs `lib/lanesServer.ts` is the template pattern).

Inputs (env-pathed in `.env.local`):
- **BQ** `ejam-dwh.production.creative_dashboard` (+ `facebook_dashboard_comments`) via
  `lib/bq.ts` (SA creds) + SQL builders in `lib/queries.ts`, 10-min TTL cache.
- **Lanes** `LANES_DIR` → `~/brain/systems/research-agent/output/lanes/latest.json`,
  generated nightly 01:06 by `~/systems/research-agent/lanes/build-lanes.mjs` (Gemini 2.5
  Flash tagging). Fallback: committed fixture.
- **Winners archive** `WINNERS_JSONL` (`~/brain/projects/2026-05/ClickUp Connection/winners.jsonl`);
  Winners view is BQ-first (`winnersSql`), ClickUp/JSONL fill-only.
- Research/Atria/Swipe/comments-digest dirs; feedback + override JSONL ledgers.
- ClickUp writes are safe-by-default (`CLICKUP_WRITE_ENABLED` gate, `CLICKUP_DRY_RUN` override).

## Branch map (verified against git, not memory)

| Branch | vs main | State |
|---|---|---|
| `feat/brain-tab` (checked out) | +34/−0 | Active superset; **contains all 12 feat/research-lanes commits** plus Brain tab, BQ-first winners/perf re-key, date-range picker, retro/brief fixes. Local-only, unmerged |
| `feat/research-lanes` | +12/−14 | Fully absorbed by feat/brain-tab; redundant once brain-tab merges |
| `feat/research-action-queue` | +0/−42 | Fully merged to main 2026-06-14 (the KARIMO-trial feature, cherry-picked clean). Deletable |
| `feat/generate-brief-from-feed` | +6/−14 | Same tip as `feat/clickup-filename-tool` (700174d). Feed→brief itself already in main; carries KARIMO plugin (~35k lines under `.claude/plugins/`), the filename tool, and one unmerged useApi QA fix (382c575) |
| `karimo-trial` | n/a | **Not a branch in this repo** — lived in torn-down worktree `~/personal/ccc-karimo-trial`; feature landed via feat/research-action-queue. Listed in the task prompt but does not exist locally or on origin |
| `iterate-button-image` | +9/−24 | Parked per `docs/TODO.md`: full ClickUp-posting Iterate button; main uses simpler brief flow |
| `design-refresh`, `design-v3`, `fix-perf-and-today` | merged | Deletable |

Origin has only main + 3 branches; box has no GitHub creds (https fetch fails, no gh) —
pushes/PR state need the Mac.

## Known bugs / open questions (flagged in CLAUDE.md)

1. **All 12 live lanes have `suggestedBrief: null`** → "Brief this lane" button never renders.
   Root cause found: `~/systems/research-agent/lanes/score.mjs:64` hardcodes `null`; the
   spec's optional "Gemini pass 3 (suggest)" was never implemented. Open question for Tomas:
   implement pass 3 in the generator, or drop the field/UI.
2. SCALE verdict advisory-only (no forward signal on the undercounted revenue basis — ROADMAP).
3. Green build/tests don't prove live surfaces: `.env.local` is runtime-required; `lib/config.ts`
   defaults are Mac-era and wrong for the box.

## Verify baseline (recorded)

`scripts/verify.sh` = lint → tsc --noEmit → vitest → `NEXT_DIST_DIR=.next-build npm run build`
→ smoke (`next start` :3105, curl `/` + `/api/research/lanes`). Designed to never clobber the
live server's `.next`. **Baseline 2026-07-06: ALL PASS — 34 test files, 380 tests, build +
smoke green** (`scripts/verify-baseline.txt`). Any future FAIL is a regression.

## Caveats

- The "before" commit is empty (`--allow-empty`): the only pre-existing dirt was `.claude/worktrees/`
  agent worktrees (nested `.git` + `.env.local` copies) which must not be committed.
- New files were committed on `feat/brain-tab` (the live branch); they ride along when it merges.
- `verify-baseline.txt` is a third new file not named in the task but referenced by CLAUDE.md's
  VERIFY section — added so "fails only on baseline-known checks" is checkable.
