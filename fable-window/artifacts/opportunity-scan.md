# Opportunity Scan: Highest-Leverage Automation Not Yet Built

2026-07-03, fable-window task 11. Inverse of the 07 waste audit: this hunts missing leverage on the existing stack (BQ, ClickUp MCP, winners.jsonl, gbrain, Hermes, CCC, ~/systems cron suite). Nothing here is built; each entry is a build sketch.

## The actual weekly loop (reconstructed from cron fleet + memory)

What is already automated (systemd user timers, all verified live 2026-07-03):
- Mon 04:00 winners-refresh, Mon 04:45 sha-weekly-report, daily 02:30 bq-clickup-perf writeback, Tue 04:00 comments-digest, Tue 05:00/05:30 feedback + task-lessons synth, daily 01:00/01:45 research lanes + monitor, daily 06:30 watchdog.

What Tomas still does by hand, in chat, every week (the leverage gaps):
1. **Mon-Tue: read the weekly report, pick winners, write the week's briefs.** Every brief is a fresh interactive session: muse question, LP question, angle canon check, naming, 3-block template, launch defaults. The corrections memory trail (feedback_launch_task_defaults, feedback_sha_task_angle_canon_naming, feedback_ask_muse_before_brief, feedback_parallel_brief_differentiation) is literally a log of this step going wrong repeatedly.
2. **Mid-week: performance triage.** bq-clickup-perf writes fields daily, but nothing tells Tomas anything. KILL/SCALE/fatigue verdicts exist in CCC lib/rules.ts and only fire if he opens the dashboard. Decisions between Mondays happen ad hoc in chat (/ad-review).
3. **On approval: launch-details fill.** Ryan Salud comments "can we please have the launch details", then a manual 4-field fill per task (project_sha_launch_details_fill). The launch-autofill agent that covered this was removed 2026-06-15 after the subtask incident; the need did not go away, the automation did.
4. **Ongoing: compliance.** Sweeps are manual (/compliance-scrub, the 2026-06-23 and 2026-06-30 sessions in KB compliance-sweep-methodology). Meanwhile bans keep changing (3 new hard rules 2026-06-30 alone). Nothing scans active tasks continuously.
5. **Never: closing the brief-to-outcome loop.** winners.jsonl + BQ know which briefs won; the lesson extraction (Loop D, designed 2026-06-13, still queued) has never run. Winner patterns were distilled once, by hand, on 2026-07-02 (feedback_winner_patterns_2026H1).

Scoring: leverage = (hours saved/wk x error reduction) / build effort, on existing components only.

---

## Rank 1 - Monday Brief Conveyor (winner -> draft retro briefs, gated)

**Pain removed:** the single biggest weekly time block: turning Monday's winners into the week's iteration briefs by hand. The canon itself says this should be a machine: feedback_winner_patterns_2026H1 pattern 1 (43% of all winners are retros; default brief = one variable changed on a live winner) and pattern 2 (statics + headline stacks are "the winner factory... ship these weekly before commissioning video"). Every manual pass re-risks the documented correction classes (defaults forgotten twice in one session per feedback_launch_task_defaults; naming per feedback_sha_task_angle_canon_naming).

**Build sketch:** a Mon 05:30 timer (after sha-weekly-report 04:45) `~/systems/brief-conveyor/`:
1. Pull top iteration candidates: BQ `creative_dashboard` last-14d by contribution dollars with the CCC $500 spend floor (reuse `winnersSql` in `~/creative-command-center/lib/`), cross-check `winners.jsonl` so already-retroed concepts are deprioritized.
2. For each candidate, call the ALREADY-BUILT rich ITERATE brief engine: `lib/clickup.ts buildBriefPayload` with WinnerContext (why-it-won block, embedded reference image re-hosted to ClickUp, locked winner copy, vary-one-variable axis, `_retro` naming with current sprint, full custom-field inheritance incl. FB Ad3 LP). This engine shipped and was live-verified 2026-06-29 (commits ef6108f..d074dd1, project_ccc_research_lanes); the conveyor is just a headless caller.
3. Gate: post to ClickUp with status `backlog` (drafts), or write a review file + ntfy one tappable CCC URL (topic tomas-tab-958e4431, per feedback_browser_url_handoff). Tomas promotes backlog -> to do; LP is inherited from the source winner's FB Ad3 LP, never freshly picked (respects feedback_ask_landing_page).
4. Check every draft against the 14-pattern canon file; label any zero-pattern draft as an exploration bet (the canon's own apply rule).

**Effort:** 1-2 days. The hard 80% (brief payload, naming, field inheritance, image re-host) already exists; new code = candidate query + headless runner + timer + watchdog jobs.conf line.
**Riskiest assumption:** the brief engine lives on unmerged branches (`feat/research-lanes` committed, `feat/brain-tab` partly working-tree per memory). If that tree gets churned before the conveyor wraps it, the 80% head start evaporates. First move: commit/merge or at least freeze the brief-engine code path.

**Why rank 1 over rank 2:** it automates the value-creating step, not a hygiene step. Briefs are the output of Tomas's job; 5-10 go out weekly and each costs 20-40 min of session time plus correction round-trips. Rank 2 saves real hours too, but it protects spend rather than producing assets, and its verdict logic needs calibration before it is trustworthy. The conveyor's core logic is already trusted (Tomas iterated it live through ~10 commits in June); leverage = highest hours x highest plumbing-readiness.

---

## Rank 2 - Daily KILL/SCALE/Fatigue Push (verdicts leave the dashboard)

**Pain removed:** mid-week performance decisions currently require Tomas to open CCC or start an /ad-review chat. The rules engine (lib/rules.ts SCALE/KILL/WATCH/KEEP + materiality-aware fatigue: FATIGUE_MIN_SPEND=200, ROAS drop >=10%, CTR drop >=15%, per project_creative_command_center) already computes verdicts daily against fresh BQ; they are display-only. A dying ad found Thursday instead of next Monday is direct spend saved.

**Build sketch:** `~/systems/verdict-push/` daily 07:00 timer (after bq-clickup-perf 02:30): curl the CCC action-feed API on localhost:3000 (creative-command-center.service is always-on), diff verdicts against yesterday's state file (only NEW KILL/SCALE/fatigue fire), emit a 5-line digest -> ntfy tomas-tab-958e4431 + a comment on the matching ClickUp task via `~/.config/clickup/pk` REST (the SH-#### mapping already exists in bq-clickup-perf's clickup_project join). No LLM call needed; pure diff-and-format.
**Effort:** half a day.
**Riskiest assumption:** verdict quality at daily granularity. BQ revenue is first-order only, no LTV (project_ccc_research_lanes data decision), so cmROAS-based KILLs can misfire and alert fatigue would kill trust in week one. Mitigation: ship WATCH-silent, KILL/SCALE-only, with the reason string attached.

---

## Rank 3 - Launch-Details Fill Assistant (comment-triggered, draft-gated)

**Pain removed:** the "can we please have the launch details" -> 4-field manual fill loop on every approved video (FB Ad3 LP + Landing Page Link mirror, FB Ad4 FB Page, FB Ad6 Headline, FB Ad7 Text; project_sha_launch_details_fill). Happens per approved asset, several times weekly, and it blocks the media buyer until done.

**Build sketch:** `~/systems/launch-fill/` polling timer (2x daily): filter Creative Strategist list (901110066469) for parent tasks in `approved` with a Ryan Salud comment matching /launch details/i and empty FB Ad6/Ad7. For each, DRAFT the fill: copy sourced from precedent (`tasks_since_2025-09-30.jsonl` .fb_ad fields, jq) or the sibling task of the same concept (the Goodbye Letter reuse pattern), competitor names genericized per the memory rule. Post the draft as a ClickUp comment @Tomas + ntfy with the task URL; write fields only after his reply/reaction. Reuse the patched `~/systems/launch-autofill/autofill.py` guards verbatim: subtasks=false + parent-only + creator!=ClickBot triple guard, never touch the Channel field.
**Effort:** 1 day (most guard code exists in the disabled autofill agent).
**Riskiest assumption:** Tomas REMOVED launch-autofill himself on 2026-06-15. The bet is that the objection was scope (proactive mass-fill on 5 statuses, 256-subtask incident) not the concept, and that a narrow comment-triggered draft-first version is welcome. Confirm before building; also LP remains a per-task human call, so the draft proposes and never auto-picks.

---

## Rank 4 - Continuous Compliance Sweep (scorer as a cron, not a session)

**Pain removed:** compliance sweeps are manual multi-hour sessions (2026-06-23 sprint sweep, 2026-06-30 multi-surface audit per KB compliance-sweep-methodology) while the banned list mutates fast (sucralose correction, real-fruit, made-in-USA, dye-free all landed within 10 days). Between sweeps, non-compliant copy sits in active tasks and can ship to paid.

**Build sketch:** `~/systems/compliance-sweep/` weekly timer (Wed 05:00, off-peak per the headless-cron rule): pull active-status tasks from list 901110066469 (to do / in progress / cs review / approved / sent to mb) via REST, extract description + FB Ad6/Ad7 fields, run each through the EXISTING deterministic `~/systems/compliance-eval/scorer.py` against policy.json (patched to 2026-07-03, precision=recall=1.0 on 15 fixtures). Output a diff-ready fix list like /compliance-scrub, save via the reports pattern, ntfy on any HARD hit with the task URL. Zero LLM tokens; the scorer is regex.
**Effort:** half a day. The scorer, policy, and token all exist; new code is the ClickUp fetch + field extraction loop.
**Riskiest assumption:** regex coverage. The night-1 hard-case work marked 12/20 new baits as policy_gap (regex cannot catch implied claims). A green sweep must be reported as "no KNOWN banned phrases", not "compliant", or it creates false confidence. Pairing each HARD hit with the rule id keeps it honest.

---

## Rank 5 - Loop D: Brief -> Outcome Lessons (the flywheel that compounds)

**Pain removed:** every brief is written without systematic knowledge of how its predecessors performed. The winner-pattern canon proves the value (14 patterns from one manual 2026-07-02 distill) but it is a snapshot that goes stale; Loop D (project_creative_feedback_loop) was designed to keep it live and "has rich data NOW... consider D first when resuming" per the memory itself.

**Build sketch:** extend `~/systems/creative-feedback/` (the synth pipeline is built and cron'd Tue 05:00): new `brief_outcomes.py` joins winners.jsonl records (tags, editor_code, sprint, win_signal, perf snapshots) + BQ ROAS by clickup_project to the brief attributes parsed from task names (angle, format, test type, retro-vs-new). Emit per-attribute win-rate/ROAS stats as a third synth_prompt block, flowing into the existing proposals.md -> /feedback-promote gated path, protected by the existing keep_best_gate.py compliance gate. Promotions update feedback_winner_patterns_* canon so the Rank-1 conveyor and the script skills read fresher priors every month.
**Effort:** 1-2 days, mostly the join and stats code; the synth/promote/gate scaffolding all exists.
**Riskiest assumption:** join quality. Name-token parsing is dirty (83 of 334 spend records unparsed in the canon distill) and SH-code -> BQ matching is ambiguous in known cases (SH-16142 under two concepts; match on post_link per memory). If the join is <80% clean the stats mislead rather than inform; budget the first half-day purely for join validation against the canon's hand-checked numbers.

---

## Shortlist (one line each)

- **Cross-session actions ledger:** nightly job greps all of today's transcripts for ClickUp create/update results into a queryable daily jsonl, killing the documented wrong-answer class in feedback_recall_search_before_answering (half day).
- **Video-iteration ClickUp templates (step two of project_clickup_video_iteration_system):** turn the approved 10-type taxonomy into clickup-task-creator profiles, weighted by which types actually graduated in winners.jsonl (1 day).
- **Atria weekly swipe cron:** `atria_swipe_pull.py` is still on-demand ("could mirror the systems pattern", project_atria_integration); a Mon timer keeps the CCC swipe gallery and lane engine fed without asking (2 hours).
- **Wiki-performance-sync draft mode:** monthly cron runs the existing skill logic to DRAFT canon-page updates to wiki-drafts/ for human apply, same human-gate as research ingest (half day).
- **Approved-script -> SHA Doc automation:** on a script hitting approved, auto-create the canonical 2-table Google Doc from the template (project_shameless_script_template); currently manual per script and blocked only by Drive auth mode on the box (1 day, needs gws work-account path).

## Ranking logic in one line

Build order = conveyor (creates assets, plumbing ready), verdict push (saves spend, trivial build), launch fill (unblocks the buyer, needs Tomas's yes), compliance cron (cheap insurance), Loop D (compounds everything above but slowest payback).
