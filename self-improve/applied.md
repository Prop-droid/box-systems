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
