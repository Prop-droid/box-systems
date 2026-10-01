# CCC review — performance — 2026-09-13

TL;DR
- Sunday bug in `lastNWeeks` drops the freshest full week every Sunday — users see week-old data as "current" (`lib/weeks.ts:42`)
- API error on /work + /performance silently shows "$0" KPIs and "Nothing to show" — pipeline failures are invisible to users
- Empty 200 BQ responses cached 10min server + 10min client — outage silently shows empty state for up to ~20min with no error
- NEW verdict chip always returns 0 rows from non-`'new'` preset; WATCH chip permanently 0 — both are dead UI buttons
- Two Mac-era `config.ts` defaults (`sha-systems`, `-Users-tomas`) break memory + feedback dirs if `.env.local` is missing
- FunnelView fires a full `funnelAllSql` BQ query on every page load even in single-LP view — silent slot waste

## Findings

**[SEV: high]** Sunday edge: `lastNWeeks` subtracts 7 days when today is Sunday, dropping the freshest full week — `lib/weeks.ts:42` — `dow = (0+6)%7 = 6`; `lastSun = add(today, -7)` skips current week entirely — fix: `-((dow + 1) % 7)` so Sunday yields 0 offset

**[SEV: high]** RowList shows "Nothing to show for these filters" on API error, indistinguishable from zero-ads — `app/components/WorkView.tsx:468-469` — `crError` is threaded to KpiBand but never to RowList — fix: add `error` prop to RowList with a distinct error message

**[SEV: med]** Outage-cached-as-empty: silent `200 []` from BQ cached 10min server-side then 10min client-side — `lib/cache.ts:14-15` + `useApi.ts:48-49` — only thrown errors evict cache; empty-success looks like real no-data for ~20min — fix: routes expecting non-empty results return 503 on empty

**[SEV: med]** KPI band cells (SPEND/REVENUE/CONTRIB/ORDERS) render `$0` on API error, not `—` — `app/components/WorkView.tsx:431-435` — only cmROAS cell has the `error ? '—'` branch — fix: propagate `error` to every `<Kpi>` cell

**[SEV: med]** NEW verdict chip always returns 0 rows from any non-`'new'` preset — `app/components/WorkView.tsx:232-234` + `lib/workRows.ts:52-65` — `pickVerdict('new')` sets `preset='all'` but `toWorkRows` only emits `verdict='NEW'` for `source==='new'` — fix: `pickVerdict('new')` should switch to `preset='new'`

**[SEV: med]** WATCH verdict chip permanently shows `WATCH 0` with no explanation — `lib/workRows.ts:59` — `fatigued: false` hardcoded for creatives source; `creativeVerdict` never returns WATCH without fatigue data — fix: hide chip or label `(no fatigue signal)`

**[SEV: med]** `lastNDaysRange` passes raw local `Date` to `toISOString()`, window is 1 day short 00:00–03:00 EET — `lib/weeks.ts:16` + `WorkView.tsx:136` — `lastNWeeks` already has `Date.UTC(...)` normalization with a comment explaining why; `lastNDaysRange` does not — fix: mirror same pattern

**[SEV: med]** Two Mac-era stale defaults in `lib/config.ts` break silently when `.env.local` is incomplete — `lib/config.ts:13-14` — `feedbackDir` → `~/sha-systems/creative-feedback` (retired), `memoryDir` → `-Users-tomas` (Mac path) — fix: box-correct paths or make env vars required

**[SEV: med]** `funnelAllSql` BQ query fires on every render even in single-LP view — `app/components/FunnelView.tsx:107` — `allUrl` is always non-null; results are memoized but never rendered in single view — fix: `const allUrl = view === 'all' ? \`/api/funnel?all=1&...\` : null`

**[SEV: med]** Leaderboard all-empty boards ambiguous on ETL failure — `app/components/LeaderboardsView.tsx:23` — null `first_seen` silently drops all rows, renders "Nothing launched in this window yet" — fix: include `rowsTotal` in API response; show warning when BQ has rows but boards are empty

**[SEV: med]** FunnelView LP dropdown fires duplicate BQ query — `app/components/FunnelView.tsx:81` — `lpListUrl` omits `priorFrom`, different cache key from LpTable's; two separate BQ calls per tab render — fix: derive slugs from LpTable's already-loaded data

**[SEV: med]** 🌱 + 💰 underfed flags can stack on a new LP — `app/components/LpTable.tsx:106` — `rowFlags` has no `is_new` guard in underfed branch; 2-day-old LP with noisy ROAS≥1.2 gets "shift budget here" on meaningless data — fix: `if (r.is_new) return flags` after pushing the new badge

**[SEV: med]** Fatigue badge uses 8-week window while card metrics reflect user's selected range — `app/components/CreativeDetail.tsx:233-239` — no label distinguishes the two windows — fix: add `"based on 8w trend"` to badge tooltip

**[SEV: low]** Missing `adId` null guard in leaderboard expanded thumbnail — `app/components/LeaderboardsView.tsx:72` — collapsed row guards it (line 42), expanded panel does not; empty `adId` → 400 → broken image — fix: same guard in expanded panel

**[SEV: low]** KPI band totals span user's date-range while Winners list spans `winnersDays` with no label — `app/components/WorkView.tsx:246` — "Last 14 days" KPI alongside a 90-day winners list is actively misleading — fix: label "KPI: 14d · List: 90d" when `preset==='winners'`

**[SEV: low]** `creativeDailySql` exported from `lib/queries.ts` with zero callers — `lib/queries.ts:498` — dead code — fix: delete or comment with `// TODO: wire to /api/creatives/daily`

**[SEV: low]** `topOverall` in `lib/leaderboards.ts` is dead code — `lib/leaderboards.ts:43` — only its own test imports it; board switched to `topByType` (ec8dab2) — fix: remove export and test fixture

**[SEV: low]** `cmRoasColor` duplicated verbatim in two files — `WorkView.tsx:81` + `CreativeDetail.tsx:188` — threshold change requires two edits — fix: extract to `lib/fmt.ts`

**[SEV: low]** ClickUp workspace team ID hardcoded in `CreativeDetail.tsx:449` — no env reference; silent breakage on workspace change — fix: define `CLICKUP_TEAM_ID` in `lib/config.ts`

**[SEV: low]** `useApi` truncates BQ error messages to 200 chars — `useApi.ts:60` — useful identifiers often appear past char 200; harder to triage during outages — fix: raise cap to 500 or `console.error` full message before slicing

## Verdict

The performance slice has two acute correctness issues that silently mislead operators: the Sunday week-boundary bug makes the dashboard show week-old data as "current" one day per week, and the lack of error-vs-empty distinction means a broken BQ pipeline looks identical to a zero-spend day. The single highest-value fix is the `RowList` error-state + cache-empty 503 pattern (findings 2 + 3 together) — it removes the entire class of silent-failure confusion across every performance surface.

---

Report saved to `~/systems/ccc-review/reports/2026-09-13-performance.md`. 20 findings: 2 high, 11 med, 7 low.
