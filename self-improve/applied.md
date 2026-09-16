# Applied self-improve proposals

(append-only; each entry = date, proposal id + one-liner, proof)

## 2026-08-13 — P1 (variant): SessionStart hook no longer drops daily log + budget note
Source: token-audit 2026-08-01. P1 proposed raising the 6,000-char cap to 12,000;
applied a better fix instead — section budgeting — so always-on context stays flat
at 6,000 rather than growing (which the same audit flagged as the problem). The
index preview now gets only the char budget left after the fixed sections, so the
daily log and Context Budget note are always kept.
Proof: `hooks/session-start.py` build_context() reserves fixed sections first;
verified all 4 sections present at exactly 6,000 chars, no tail truncation.
File: ~/.tools/claude-memory-compiler/hooks/session-start.py (no VCS in that dir;
rollback snapshot: hooks/session-start.py.applied-2026-08-13).

## 2026-08-13 — P2, P9, P10 (memory pruning; state had drifted from the proposals)
- P2 (delete stale/conflict memory files): 2 sync-conflict files + `project_24_7_agent_box_and_search_build.md` were ALREADY gone. Deleted the one remaining, `project_iteration_suggestions_drop.md` (timer self-disabled, END_DATE 2026-07-17 passed, confirmed no live timer, no MEMORY.md index line). Backup: `~/systems/self-improve/archive/2026-08-13/`.
- P9 (trim CLAUDE.md < 9,000): ALREADY SATISFIED. `~/.claude/CLAUDE.md` was 6,486 chars (slimmed 2026-08-10, after the audit measured 11,710). No change made; trimming further would drop useful content.
- P10 (cap index): added `~/.tools/claude-memory-compiler/scripts/cap_index.py` (deterministic; keeps newest 60 index rows by Updated date, article files untouched) and wired a best-effort call into `compile.py` main(). Applied once: index 119 lines/38,185 chars -> 64 lines/24,587 chars (55 rows evicted). Backup: `archive/2026-08-13/index.md.bak`.
Proof: `cap_index.py --dry-run` reports 0 further evictions; compile.py parses; drop-note gone.

## 2026-08-25 — P1, P2, P3 (Tomas in #ops-log 09:39, dispatched via #dev)
- P1 (re-index wall-copy rule): added `feedback_wall_copy_emotion_over_proof.md` line to MEMORY.md under "Shameless — brand canon & copy rules". File confirmed present (2.5K).
- P2 (skill-sync for 18 dead symlinks): ALREADY SATISFIED — deep scan found 0 dead symlinks under `~/.claude/skills` (in fact 0 symlinks at all; skills are real dirs now); all 9 named skills (firecrawl-*, comfyui, hermes-agent, ffmpeg-analyse-video) resolve. `~/.claude/skill-sync.sh` no longer exists. No action.
- P3 (response-brevity memory): wrote `feedback-response-brevity.md` with the proposed body, indexed under "Working style", `mark_promoted.py tl_08e81602 tl_27b79840 tl_08d243b9` → OK promoted 3 of 3.
Proof: grep wall_copy/brevity MEMORY.md hits; find -xtype l = 0.

## 2026-09-01 — P1-P4 applied (Tomas: "Self improve p1 p2 p3 p4", Telegram migration topic)
- P1: session-start.py now caps index summary cells at 80 chars — 19 rows visible per session (was 2-3), context steady at 6,000 chars. Verified by executing build_context().
- P2: MEMORY.md hooks fixed (Telegram = Phases 1-3 shipped; SFF build = Route B AM5+9060XT ~€1,005; Linux-beginner line unbundled). project_sff_tv_gaming_build.md body + description marked DECIDED. project_telegram_migration.md body was already current (updated 08-31); only the index line was stale. feedback_linux_beginner_stepwise.md deleted; no matching gbrain page existed (verified via gbrain list) — nothing to delete there.
- P3: both *.sync-conflict-* files deleted from memory dir (0 remaining).
- P4: clickup-task-creator SKILL.md — new gotcha 6 (description PATCH silently drops due_date, SH-18111 ×2/SH-18113/SH-18159) + Step-7 line: re-read due_date after any description patch, re-set + re-verify on drop. Backup at SKILL.md.bak-2026-09-01.

## 2026-09-01 — P5-P10 applied (Tomas: "sil imrpoove p5-p10", Telegram migration topic)
- P5: feedback_no_visual_direction.md written verbatim from prop_f1a76b08 + MEMORY.md pointer under Copy & script craft.
- P6: patchright installed in ~/systems/ig-ingest/cloak-venv; import verified.
- P7: tl_b9d16e97/tl_56f5e51a/tl_59156fa5 marked promoted (3/3); gbrain page lessons/clickup-task-creator/canon-no-excess-content written + read back. Both task-lessons proposals flipped to promoted, proposals.md re-rendered.
- P8: session-end.py reconcile_memory_index() — watermark-gated (only files newer than last run auto-append, so hygiene-pruned files stay pruned), appends under '## Unfiled (auto-indexed)'. Self-tested end-to-end with a temp memory file: appended, then cleaned up.
- P9: CCC .cache/rules-overrides.json SPEND_FLOOR 250 (default 500, source prop_b3a91f2c) — the engine's designed override path, verified live via loadOverrides()+threshold() = 250; no rebuild/restart needed. Compiled default in lib/rules.ts untouched. prop_b3a91f2c marked promoted.
- P10: brand='SHA' trap documented in clickup-task-creator Step-1 (BQ pulls bullet) + reference_ejam_bigquery.md bolded — the skill had no literal "Step-0 BQ block", anchored where agents actually gather inputs.

## 2026-09-08 — P1-P10 applied (Tomas in Ops Log: "@agentbox_dev_bot apply all fixes")
- P1: ALREADY SATISFIED (applied 2026-09-01) — session-start.py slim() caps cells at 77+"..." (lines 87-94); this session's own index preview shows ~19 truncated rows. No change.
- P2: feedback_percentage_claims_recompute.md written with retro 2026-09-06 body verbatim + MEMORY.md pointer under Shameless canon (next to full-sugar-candy comparator).
- P3: root cause was NOT an IP in the skill (no 192.168.0.38 anywhere in code — ghost from an ad-hoc probe): `ssh mac` alias still pointed at `eJam-Tomas-Saltis-2.local`, which stopped resolving after the 08-28 subnet split. Fixed ~/.ssh/config Host mac → 100.68.166.21 (Tailscale); `ssh mac` verified OK. Gotcha line added to fleet-control SKILL.md ("never probe the Mac on 192.168.x from the box").
- P4: feedback_surgical_edit_execution.md written with retro body verbatim + MEMORY.md pointer paired with feedback_literal_muse_copy_over_strategy.
- P5: ALREADY SATISFIED — project_telegram_migration.md was fully rewritten 08-31/09-01; the routing canon the proposal asks for is already locked in the "ROUTING CUTOVER" section (coach → Coach group, all creative/marketing → Creative Feed, failure alerts → Dev Ops Log, ccc-review stays Dev). Proposal evidence ("still reads Phase 1 only") was a stale snapshot. No change.
- P6: feedback_reminders_via_discord.md deleted + MEMORY.md pointer line removed (was already marked SUPERSEDED/propose-delete).
- P7: ALREADY SATISFIED (applied 2026-09-01) — zero *.sync-conflict-* files in the memory dir. No change.
- P8: auto-memory file + pointer were already gone (09-01), but the gbrain HALF was NOT: `memory/feedback_linux_beginner_stepwise` (page 1643) still existed — the 09-01 "no gbrain page" check was wrong (CLI list vs MCP search). Soft-deleted via delete_page (restorable 72h; autopilot purges after).
- P9: gbrain page lessons/bq-clickup-perf/canon-clickup-api-transient-failures written with prop_a3f7b2c1 body (created_or_updated, 1 chunk); mark_promoted.py tl_15be4430 tl_0ccc9fd2 tl_a598e677 → OK 3/3 (note: ids must be SPACE-separated — comma-joined promotes 0).
- P10: DEVIATION — proposal's "Route B AM5 ~€1,005" hook is stale; the file's own BOM LOCKED section (08-31, Tomas-approved) + 09-01 Varle quote show the real decision = DeskMeet B760 + i5-12400F + Reaper 9060 XT, €931 all-Varle. Rewrote the file to that truth: 346 → 65 lines (final BOM, rationale, cooling mods, known issues, upgrade paths, open threads: Varle quote terms + Wi-Fi module model). MEMORY.md hook fixed to "BOM LOCKED: DeskMeet B760 + 9060 XT, €931 Varle".
Proof: ssh mac = SSH-MAC-ALIAS-OK; gbrain put status created_or_updated + delete status soft_deleted; mark_promoted 3/3; wc -l sff file = 65; grep MEMORY.md shows 2 new pointers, 0 reminders_via_discord.

## 2026-09-16 — P1-P10 applied (Tomas in Ops Log: "Apply feedback")
- P1: feedback_clickup_instructions_5bullet_cap.md written (5-bullet cap, no why-sentences/narration) + MEMORY.md pointer under ClickUp section.
- P2: feedback_verify_canon_at_task_start.md written (numbers from live checkout/canon, never wiki prose) + pointer paired with percentage-claims line.
- P3: SHA weekly report — root cause: Sonnet sometimes emits the full report with ## sections but no "# " H1; validator discarded 3 valid 11-27KB attempts on Sep 7 (Sep 14 passed on retry 2, report.md exists, 475 lines — ad-review unblocked). Fixed both ends: report_prompt.txt now hard-requires the exact H1 first line, and run_report.sh gained a salvage branch (≥8KB + "Shameless Snacks" + ^## present → prepend canonical H1 instead of exit 3). bash -n clean.
- P4: gbrain page lessons/clickup-task-creator/canon-workflow-rules written (prop_b5d8e4f9 body); mark_promoted tl_4557a572 tl_532f3d4a tl_fe262c61 tl_441b5d2c tl_2fc5de1b → 5/5.
- P5: ALREADY SATISFIED (09-01) — slim() row-cap live in session-start.py. No change.
- P6: (a) telegram hook already current (Phases 1-3 shipped since 08-31 rewrite); (b) folded into P7 — proposal's "Route B AM5 €1,005" text was stale twice over; (c) linux-beginner file+gbrain both already deleted (09-08). No changes beyond P7.
- P7: project_sff_tv_gaming_build.md rewritten 464 → 28 lines to REV8 truth: Caseking ORDERED (C6 white GEJB-125 + AXP120-X67), remaining Varle €734.84 (B760M-A WIFI D4 / ASUS DUAL 9060 XT / RM650e) + rde €165.01 (14400F tray + 2× P12 Pro white), ≈€1,002 total; kept fit constraints, market gotchas (re-price >1wk-old BOMs, itwork.lt veto), not-chosen forks as one line.
- P8: (a) 0 sync-conflict files existed — no-op; (b) removed duplicate feedback_telegram_only_texting.md pointer (was on 2 lines); (c) hook-rate files merged → feedback_hook_rate_doctrine.md, originals deleted, pointer updated; (d) code-things files merged → project_code_things.md, originals deleted, pointer updated; (e) nobara NOT confirmed sold (parts-sale still in progress) — archive skipped per the proposal's own conditional.
- P9: (a) ALREADY FIXED 09-08 — 192.168.0.38/mac-alive is a phantom endpoint (exists in no config); real fix was ssh mac → Tailscale 100.68.166.21, still green; (b) Perplexity retested live: 2,362-char cited answer (the 09-01 93-char extraction bug self-resolved) — CLAUDE.md already leads research with Perplexity and never mentioned the perplexity-research skill, so no edit; memory note updated. NOTE: session token expires ~Sep 24 — refresh due next week (Tomas pastes cookie per project_agentbox_perplexity_mcp.md).
- P10: ALREADY LIVE since 09-01 — CCC .cache/rules-overrides.json SPEND_FLOOR=250 (verified today); prop_3a9f1c72 flipped to promoted in creative-feedback proposals.jsonl with note. The compiled default 500 stays by design (override path is canonical).
Proof: bash -n OK; gbrain put created_or_updated; mark_promoted 5/5; wc -l sff = 28; MEMORY.md grep = new pointers present, dupes gone; perplexity LEN:2362.
