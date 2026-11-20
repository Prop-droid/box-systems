5 parallel subagents launched — /work, /performance, /leaderboards, /funnel+LPs, and cross-cutting. Waiting for results to synthesize the full report.

Cross-cutting agent done. Waiting for the remaining 4 (/work, /performance, /leaderboards, /funnel+LPs).

/funnel+LPs done. Still waiting on /work, /performance, /leaderboards.

/leaderboards done. Still waiting on /work and /performance.

/work done. Still waiting on /performance.

# CCC review — performance — 2026-11-08

TL;DR
- Cache stores empty BQ results as valid data — a pipeline gap goes undetected for up to 70 min (server + client TTLs stacked)
- Fatigue signals (CTR sparklines) mix Facebook + Google spend — an ad looks fatigued when only its Google CTR is declining
- /work board hit-rate delta arrows compare different time horizons — current cohort always looks better by construction
- `today` computed once on mount; dashboard open past midnight quietly shows windows shifted one day back
- /funnel all-funnels grid shows ghost LP cards ($0 current spend) — no spend floor in funnelAllSql
- Two Mac-era config defaults in lib/config.ts silently misdirect file I/O on Linux if .env.local is incomplete

## Findings

[SEV: high] Empty BQ result cached as valid data (server) — `lib/cache.ts:11-18` — `withCache` stores the promise before resolution; `.catch` evicts only on thrown errors, not on `[]` success. A pipeline gap returns 0 rows and those rows are served for the full TTL (up to 1 hr for accountHealthSql). — Fix: guard on row count in route handlers; treat unexpectedly-empty results as 503 so the cache evicts them.

[SEV: high] Same pattern stacks on the client — `app/components/useApi.ts:48-50` — Client caches the server's 200+[] for 10 min. Combined worst case: 60 min server + 10 min client = 70 min of silent empty boards during an outage.

[SEV: med] trendsSql has no channel filter — `lib/queries.ts:228-237` — Every other channel-sensitive query adds `AND channel='facebook'`; trendsSql does not. For ads on both Meta and Google, Google's CTR mixes into fatigue sparklines. — Fix: add `AND channel='facebook'`.

[SEV: med] hitRateOf prior-window asymmetry — `lib/workBoards.ts:139-156` — Current cohort is measured lifetime (upload→today); prior cohort measured only within the prior date slice. Delta arrows on tested/winners/hitRate always favor current by construction.

[SEV: med] `today` frozen at mount, boards stale across midnight — `app/components/WorkView.tsx:75` — `useMemo(() => new Date().toISOString().slice(0,10), [])` runs once; after UTC midnight all board windows shift backward silently.

[SEV: med] cruva-trybe segment mislabels image ads — `lib/segments.ts:14` — No `asset_type==='VIDEO'` guard; description says "Creator videos." Any image ad with "cruva" in the name inflates the segment and hides from Untagged.

[SEV: med] Ghost LP cards in all-funnels grid — `lib/queries.ts:482` — `funnelAllSql` has no spend floor (unlike lpSql's >500 guard); 5 stale prior-only LPs show as ghost cards with $0 current spend.

[SEV: med] Broken `<a href="(unmapped)">` in LpTable — `app/components/LpTable.tsx:336` — `'(unmapped)'` is truthy; confirmed live on 1 of 11 current LP rows. — Fix: check `row.url !== '(unmapped)'` before rendering the anchor.

[SEV: med] LP parameter unsanitized in SQL — `lib/queries.ts:213` — `lp` interpolated directly; LP names with `'` cause BQ syntax error on the funnel drill path.

[SEV: med] Expanded leaderboard image unguarded on empty adId — `app/components/LeaderboardsView.tsx:72` — Collapsed thumbnail is guarded; expanded panel is not. Empty adId → `/api/thumbnail/` → 404 → broken image.

[SEV: med] Mac-era memoryDir default — `lib/config.ts:17` — `-Users-tomas` segment wrong on Linux; set `MEMORY_DIR=/home/tomas/.claude/projects/-home-tomas/memory` in `.env.local`.

[SEV: med] Mac-era feedbackDir default — `lib/config.ts:15` — `~/sha-systems/creative-feedback` retired on this box; set `FEEDBACK_DIR` to current path in `.env.local`.

[SEV: med] creativeDailySql dead export — `lib/queries.ts:599-612` — Nothing imports it outside tests; implies a non-existent daily-drill route. Remove it.

[SEV: low] No `from <= to` guard in /api/creatives — `app/api/creatives/route.ts:38-39` — Reversed range returns 200+[] silently.

[SEV: low] funnelAllSql near-zero rows ($3–$8 spend) — `lib/queries.ts:482-500` — Statistically meaningless funnel rates appear in the all-mode grid alongside the ghost cards; same fix as the floor finding above.

[SEV: low] MTD prior window definition unexplained — `lib/workBoards.ts:31-39` — Prior = last-N-days before MTD start (not same-period-prior-month); no tooltip.

[SEV: low] FunnelView fetches allUrl unconditionally — `app/components/FunnelView.tsx:107-108` — Full BQ funnelAllSql scan fires on every single-funnel render. Fix: `allUrl = view === 'all' ? url : null`.

[SEV: low] runQueryCached MIN_10 TTL on 365-day firstSeen CTE — `app/api/creatives/route.ts:46` — 6 BQ scans/hour per unique window; result changes at most daily. Pass `HOUR_1`.

[SEV: low] BQ `CURRENT_DATE()` UTC vs box UTC+2/+3 — `lib/queries.ts` (multiple) — Most recent complete day appears missing from live-ads counts during Vilnius early-morning hours.

[SEV: low] /leaderboards range end is today (partial BQ day) — `app/api/leaderboards/route.ts:33-35` — Public surface displays partial-day ROAS with no indicator; use yesterday as `to`.

## Verdict

The performance slice is data-fresh across all surfaces (BQ lag 1 day, well within threshold), but carries two high-severity structural flaws: neither the server cache nor the client cache can distinguish a valid empty result from a silent pipeline failure, meaning any BQ data gap caches as empty boards for up to 70 minutes with no alert. The single highest-value fix is adding a row-count guard in route handlers before caching — treating an unexpectedly-empty BQ result as a 503 — which forces the client to retry and self-heal automatically.

---

Report saved to `~/systems/ccc-review/reports/2026-11-08-performance.md`.
