# winner-mine SOURCES (task 20, 2026-07-04)

What was actually used to build `winner_patterns_v2.md`, with reproduction commands.

## 1. Winner SUBTASK mine (new evidence layer, labeled SUB)

- File: `~/brain/projects/2026-05/ClickUp Connection/winners.jsonl` (334 parents, 673 nested subtasks; archive auto-refreshed weekly Mondays, so current to ~2026-06-29).
- Population: 645 subtasks whose name starts with `MB - Winner` (Product Image 371, Video 221, Advertorial Image 53). The other 28 subtasks are work items (Write copy, Design, New Video IH, script tasks) and were EXCLUDED; v1's `complete` count (26/27) was almost entirely these work items, not variants.
- Outcome mapping: `sent to mb` = shipped (268), `abandoned` = abandoned (367), everything else = pending (10; backlog/to do/mb-testing). Keep rate = shipped / (shipped + abandoned), n = 635.
- Angle classification: case-insensitive regex over PARENT task name, same token families as the v1 distill: offer-urgency (offer|sale|clearance|last ?call|soldout|urgency|gift|bfcm|discount|allstars), reason-why (wearesorry|sorry|letter|warehouse|packing|tariff|goodbye), fiber (fiber|broccoli|noexcuse), poop-body (poop|constipat|bloat|gut), glp1-wl (glp1|weightloss|ozempic), qvc, toxic-breakup (toxic), founder-vsl (genetics|dad ?bod|confession|founder), seasonal (newyear|nynm|christmas|xmas|carnival|halloween|valentine|fall), social-proof (amazon|review|iabsolut|bestseller), comparison (usvsthem|comparison|samebag), tiktok-ugc (tiktok_ugc), whitelisting (whitelist|_wl_). Multi-match parents count in each matched lane; 94 variants under unclassified parents excluded from per-angle claims.
- Test-type classification: ImageTest, LayoutTest, CopyTest, Headline(Test), HookTest|BestHooks, Mashup tokens on the parent name.
- Headline numbers landed in v2: overall keep 42%; format keep video 65% / product-image 33% / advertorial 11%; test-type keep HookTest 71% / Mashup 59% / HeadlineTest 32% / ImageTest 23% / CopyTest 22%; angle keep whitelisting 83%, tiktok-ugc 62%, qvc 60%, glp1-wl 47%, fiber 46%, poop-body 38%, social-proof 32%, reason-why 27%, seasonal 26%, offer-urgency 25%; year drift 2025 45% vs 2026 38%; angle x format standouts: social-proof statics 0/13, reason-why statics 4/29 (14%), offer statics 31/145 (21%), offer video 11/15 (73%), fiber video 17/26 (65%).
- Semantics check run: 289/367 abandoned subtasks have meta_ad_ids populated (so "abandoned" mostly = launched then killed, not never-launched); 442 subtasks carry exactly 2 ad ids (ad + duplicate ad set), 209 carry none. Mean 2.0 variants per parent, median 1, max 16, 14 parents with 0.
- Analysis run inline with python3; no intermediate files kept. Reproducible from the regex/token spec above against winners.jsonl.

## 2. Fresh BigQuery pull (labeled BQ60), 2026-07-04

- Access: `bq` CLI with `GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/ejam-dwh-sa.json`, project `ejam-dwh`, table `ejam-dwh.production.creative_dashboard` (the only table this SA can reach). Same SA + brand filter (`brand='SHA'`) the ~/systems crons use (bq-clickup-perf, sha-weekly-report, fatigue-sentinel). Read-only queries only; narrow numeric columns per the cost rules in bq_to_clickup_perf.py.
- Query 1: GROUPING SETS ((ai_angle),(asset_type),(ai_angle,asset_type)), 60d window, SUM(spend)/SUM(revenue)/SAFE_DIVIDE roas/orders/COUNT(DISTINCT ad_id). Raw result saved at build time to /tmp/bq_angle_fmt_60d.json (ephemeral).
- Query 2: top-30 ads by 60d spend with ad_name, clickup_project, per-ad roas, and ai_formula/headline_type coverage flags.
- Query 3: IMAGE-only GROUPING SETS ((headline_type),(ai_formula)) 60d.
- Query 4: ai_angle x (prior 30d vs recent 30d) trend split.
- Headline numbers landed in v2: IMAGE $469k @ 0.86 vs VIDEO $530k @ 0.68; Scarcity 1.10 @ $77k (1.00 -> 1.21 trend), Direct Offer 0.94 @ $53k (1.03 -> 0.92), USP 1.10 @ $58k, Simple Product 0.82 @ $135k (0.79 -> 1.11), Comparison 1.05 (1.20 recent), Problem-Solution 0.59 @ $85k (0.58 -> 0.65), Curiosity 0.56 (0.44 -> 0.78); ai_formula on IMAGE: Product Aware 0.80 @ $150k, Most Aware 0.98 @ $115k, Solution Aware 1.02 @ $86k, Problem Aware 0.56 @ $83k; SH-13107-6 (Poop GLP1 headline retro) live at 1.40 @ $11.6k.
- KEY STRUCTURAL FINDING: `ai_angle`, `ai_formula`, `headline_type` are populated ONLY on IMAGE rows in this window. 100% of the $530k VIDEO spend is angle-untagged ((none)/VIDEO row). All per-angle BQ ROAS in the canon is therefore statics-only. `headline_type` is a constant 'ai' (useless as a dim).

## 3. Carried over from v1 (not re-derived)

- v1 canon file `~/fable-window/artifacts/feedback_winner_patterns_2026H1.md` (structure, patterns 1-14, archive evidence counts, wiki/TT citations). v1's own sources are in `winner-synthesis.SOURCES.md`.
- Memory files: `reference_clickup_winners_archive.md` (schema, subtask semantics hint), `reference_ejam_bq_creative_dashboard_schema.md` (ai_angle vs angle, cost rules), `project_winners_refresh_cron.md` (freshness).
- Cron scripts read for creds/filter discovery: `~/systems/bq-clickup-perf/bq_to_clickup_perf.py`, `~/systems/sha-weekly-report/queries/*.sql`, `~/systems/fatigue-sentinel/fatigue_sentinel.py`.

## Not used / missing

- Subtask-to-BQ join via `meta_ad_ids` (would give per-variant spend/ROAS, not just shipped/abandoned): skipped, ~1100 ad ids would need an IN-list query; the shipped/abandoned axis answered the task. Best next deepening step.
- Comments on subtasks: v3 archive keeps comments on parents only.
- Attachment images / visual layout analysis: still text-only.
- Cruva/TikTok live pull: TT claims remain from the wiki catalog layer.
- winners.jsonl freshness: archive refreshes Mondays; winners graduated after ~2026-06-29 are absent from SUB counts.
