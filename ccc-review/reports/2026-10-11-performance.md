5 subagents launched in parallel. Waiting for all to complete before synthesizing the final report.

Leaderboards subagent done. Still waiting on work, performance, funnel/LPs, and cross-cutting.

Cross-cutting done. Still waiting on work, performance, and funnel/LPs.

Work tab done — strong findings there. Still waiting on performance and funnel/LPs.

Funnel/LPs done. Waiting on the last one — performance tab.

# CCC review — performance — 2026-10-11

TL;DR
- KPI band CONTRIB shows gross margin (revenue−cogs), not net — missing −spend; cell shows ~$200k green while every row below shows red
- WATCH verdict is structurally unreachable (fatigued: false hardcoded) — chip permanently 0, masking 38 live fatigued ads
- New-preset video creatives silently hide Watch Behavior graph — 4 video-retention columns missing from newlyLaunchedSql
- Iterate preset renders per-ad rows, not aggregated per-creative — same creative appears 3× with split CONTRIB vs. once in All
- funnelAllSql has no spend floor — ghost LP cards ($1–$44 spend) render as funnel small-multiples with noisy conversion rates
- /api/creatives/daily route does not exist — creativeDailySql is dead exported code; endpoint hard-404s

## Findings

[SEV: high] KPI band CONTRIB is gross margin (revenue−cogs), not net contribution — `WorkView.tsx:168` — `const contribution = revenue - cogs` skips deduction of spend; per-row CONTRIB correctly uses `r.margin` (revenue−cogs−spend) from `economics.ts:3`; on live 14d data KPI shows +$104k green while row-level CONTRIB sums to −$101k; cmROAS formula is coincidentally correct — fix: change line 168 to `const contribution = revenue - cogs - spend`

[SEV: med] WATCH verdict hardcoded unreachable — `workRows.ts:59` — `fatigued: false` passed to creativeVerdict in both toWorkRows and aggregateWorkRows; `rules.ts:39` triggers WATCH only when fatigued===true; /api/trends returns 38 fatigued entries live; WATCH chip permanently shows 0; clicking it yields "Nothing to show" — fix: pre-join trends fatigue into row mapper, or hide the chip until data is wired

[SEV: med] New-preset video creatives never show Watch Behavior graph — `lib/queries.ts:385` — newlyLaunchedSql omits video_p25_count/p50/p75/video_length; /api/creatives/new returns 23 video rows all with p25/p50/p75=null; CreativeDetail:220 gates the retention section on `row.p25 != null`; silently hidden with no explanation — fix: add the 4 columns to newlyLaunchedSql mirroring creativesSql lines 70–71

[SEV: med] Iterate preset shows per-ad rows, not per-creative aggregates — `WorkView.tsx:179-183` — 'all'/'winners'/'new' all call aggregateWorkRows; 'iterate' maps raw iterRecs through toWorkRows without aggregation; a creative in 3 ad sets appears 3× in Iterate with split spend/CONTRIB vs. once in All; no label signals the difference — fix: aggregate iterRecs the same way as other presets

[SEV: med] KILL rows carry no visual badge — `WorkView.tsx:536` — SCALE and WATCH get inline colored badges; KILL condition is `r.verdict && r.verdict !== 'KILL'`, actively excluding it; live data has 66/81 raw ad rows as KILL; in 'all' view KILL rows look identical to KEEP rows — fix: add KILL badge/tint, or document the omission if intentional

[SEV: med] Leaderboards expanded panel renders broken image when adId='' — `LeaderboardsView.tsx:72` — small thumbnail guards with `{r.adId && <img>}` (line 42) but expanded panel does not; `workRows.ts:46` coerces `ad_id ?? id ?? ''` so empty string is possible; click produces GET /api/thumbnail/ which 404s — fix: mirror the adId guard on the expanded img

[SEV: med] funnelAllSql has no spend floor — ghost LP cards in "All funnels" grid — `lib/queries.ts:396-414` — live: 4 extra slugs (spend $44/$15/$3/$1) appear in the card grid vs. 13 in LpTable (which floors at $500); conversion rates off near-zero spend are noise — fix: filter cards in allFunnels useMemo (FunnelView.tsx:119) to spend ≥ 100, or add HAVING in funnelAllSql

[SEV: low] /api/creatives/daily route does not exist — `lib/queries.ts:513-526` — creativeDailySql exported but no route imports it; curl /api/creatives/daily returns 404 HTML — fix: add the route or delete creativeDailySql

[SEV: low] Winners-preset expand always sets lp: null — `WorkView.tsx:71` — winnerToCreativeRow hardcodes lp: null; winnersSql doesn't select lp column; ClickUp briefs from winners won't pre-fill the LP slug — fix: add LP regex extraction to winnersSql mirroring creativesSql line 65

[SEV: low] NEW chip shows 0 in all presets except 'new' — `WorkView.tsx:243-244` — only /api/creatives/new assigns verdict='NEW'; chip renders with 0, clicking yields "Nothing to show" — fix: hide NEW chip when tally.new === 0 and preset !== 'new'

[SEV: low] Verdict strip renders for 'winners' preset but all chips show 0-0-0-0 — `WorkView.tsx:253` — winner rows always have verdict=null; strip adds noise — fix: skip rendering when all tally counts are 0

[SEV: low] Empty result state indistinguishable from broken pipeline — `WorkView.tsx:478-479` — 200 with data:[] treated as successful empty week; only clue is spend:$0 in KPI band — fix: minimum-row sanity check or data-as-of timestamp in response

[SEV: low] Leaderboard section headings hardcode max-size counts — `LeaderboardsView.tsx:107-122` — "Top 10 images" but API returned 8; Q4 board shows 14 under "Top 30" — fix: replace hardcoded counts with data.last7.images.length etc.

[SEV: low] topOverall is dead exported code — `lib/leaderboards.ts:43-50` — not imported anywhere; earlier API shape before topByType — fix: remove

[SEV: low] Leaderboard empty-board state ambiguous — `LeaderboardsView.tsx:23` — no data-as-of timestamp; pipeline failure indistinguishable from a quiet launch window — fix: surface freshness timestamp in response

[SEV: low] Duplicate LP friendly names in scope dropdown — `lib/lpNames.ts:44` — two "IT2-VP" slugs and two "Fiber First" slugs render identically; no data corruption, but user can't distinguish them — fix: add date-token fallback suffix extractor in lpVariantName

[SEV: low] Mini-Bites LPs display as raw build strings — `lib/lpNames.ts:27-37` — SHA-Gummies-Meta-Mini-Bites-Macros ($23k) and Mini-Bites-Halloween ($11k) fall through to slug display — fix: add `{ re: /mini-bites/i, name: 'Mini Bites' }` to VARIANT_NAMES

[SEV: low] atc_to_order column has no WoW delta — `lib/types.ts:17` — prior object carries lp_to_atc delta but not atc_to_order; adjacent lp_to_atc has ▲/▼ pp delta — fix: add atc_to_order to prior fields in landing-pages/route.ts:40 and add delta render in LpTable

[SEV: low] lastNDaysRange/lastNDaysIso lack local-date normalization — `lib/weeks.ts:16-22` — lastNWeeks explicitly normalizes to avoid UTC+2/+3 off-by-one between 00:00–03:00; both lastNDays functions skip it; results in "to" date being one day behind for a 2-3h nightly window — fix: apply same `Date.UTC(local.getFullYear(), ...)` pattern

[SEV: low] funnelSql TypeScript signature lists priorTo as required but SQL ignores it — `lib/queries.ts:162` — accepted for WeekRange spread; misleads future readers — fix: mark priorTo?: string or add inline comment

## Verdict

The performance slice is live and data-fresh (BQ through 2026-10-10, all daily pipelines current). One high-severity correctness bug actively misleads: the KPI CONTRIB cell shows gross margin while every row shows net contribution — the same label, two different formulas, ~$200k apart on live data. That single-line fix (`- spend` at `WorkView.tsx:168`) is the highest-value change in this entire slice.

---

Report saved to `~/systems/ccc-review/reports/2026-10-11-performance.md`. 1 high, 6 med, 13 low findings across 5 areas. All pipelines current; no data-freshness failures.
