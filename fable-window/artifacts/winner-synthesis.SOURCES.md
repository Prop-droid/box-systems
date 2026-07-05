# winner-synthesis SOURCES (task 03, 2026-07-02)

What was actually used to build `feedback_winner_patterns_2026H1.md`, and what was missing.

## Used

### 1. Winners archive (primary, quantitative)
- `~/brain/projects/2026-05/ClickUp Connection/winners.jsonl` (v3 schema, 334 records, 3.3MB; located via the task's find command).
- Coverage: 334 parent tasks in status `mb - winner`, 201 from 2025 (S12 to S53), 129 from 2026 (S2 to S24), 4 test/legacy.
- Fields mined: `name` (angle/format/test-type token parsing), `performance_snapshots` (max spend per record as scale proxy, present on 251/334), `fb_ad.headline` / `fb_ad.text` / `fb_ad.lp` (populated on ~300), `description` (image-test headline stacks).
- Analysis run inline with python3 (token counters, angle regex clusters x spend, top-15 by spend, year splits). No file outputs kept; numbers are reproducible from the jq/python patterns in `reference_clickup_winners_archive.md`.

### 2. Wiki performance/winner pages (qualitative + ROAS cross-checks)
- `wiki/shameless/creative-strategy/top-performer-patterns-observed.md` (17 Cruva TikTok winners, hook shapes, Golden Script arc, Meta ROAS reconciliation).
- `wiki/shameless/performance/script-leaderboard.md` (14 top-spend scripts with ROAS, BQ angle-ROAS table 2026-06-02, Motion benchmarks, 7-beat structure).
- `wiki/shameless/performance/ad-performance.md` (read first ~80 lines: weekly snapshots incl. 2026-06-22 verdict, AYC x JDC hybrid observation, cmROAS caveat).
- `wiki/shameless/creative-strategy/hook-framework.md` (read first ~60 lines: four hook elements, statistic/disbelief hooks).

### 3. Memory files
- `reference_clickup_winners_archive.md` (schema, counts, caveats, query patterns).
- `project_steph_joplin_winner_pattern.md` (pattern 12 source).
- `project_winners_refresh_cron.md` (archive freshness: weekly Monday refresh, so data current to ~2026-06-29).
- `project_fable_window.md`, `project_creative_feedback_loop.md` (task framing; promote path for this canon file).

## Not used / missing

- **Live BigQuery** (`creative_dashboard`): not queried this run; ROAS figures are secondhand via the 2026-06-02 wiki refresh and may have drifted. A fresh BQ pull would tighten patterns 2, 3, 6.
- **Winner subtasks** (650 nested records incl. `meta_ad_ids`): not mined; variant-level win/abandon ratios per angle would sharpen evidence counts.
- **83/334 records with no parsed performance snapshot**: counted in evidence tallies but invisible to dollar totals.
- **Attachment images** (`attachment_urls`): visual layout patterns (colors, product framing) not analyzed; text-only distill.
- **Comments beyond win signals**: "why this won" discussion threads only sampled, not systematically read.
- **Cruva/TikTok Shop live data**: MCP available but not called; TT claims come from the wiki catalog page (pre-Aug-2025 winners known-missing there).
- **`grep "mb - winner"` in projects/docs**: hits outside the archive were scripts and raw exports (meta-brand-research), not additional winner analyses; skipped.
- **gbrain**: not queried; KB concept pages (shameless-dr-script-techniques, comparison-ad-strategy) overlap the wiki layer and were only seen via the index preview.
