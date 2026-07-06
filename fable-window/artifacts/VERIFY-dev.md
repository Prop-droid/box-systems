# VERIFY-dev.md — dev-lane verification (task 96)

Scope: CCC (`~/creative-command-center`) and `~/systems` dev-lane deliverables from
tasks 40-42 (CCC CLAUDE.md + verify.sh, systems CLAUDE.md, karpathy-guidelines v2).
All checks run live on the box 2026-07-06.

## 1. CCC CLAUDE.md + scripts/verify.sh

- Both exist: `~/creative-command-center/CLAUDE.md` (9.1K), `~/creative-command-center/scripts/verify.sh` (1.7K, executable).
- Ran `bash scripts/verify.sh` end to end (lint, tsc, vitest, `NEXT_DIST_DIR=.next-build` build, :3105 smoke):

```
lint       PASS
typecheck  PASS
test       PASS
build      PASS
smoke      PASS
```

- Matches `scripts/verify-baseline.txt` exactly (recorded all-PASS baseline). No crash, no
  regression, no discrepancy to reconcile.

**Verdict: PASS.**

## 2. ~/systems/CLAUDE.md + 3 sampled subsystem dry-runs

File exists (265 lines, `~/systems/CLAUDE.md`). Sampled 3 subsystems' documented dry-run
commands, ran each for real:

| Subsystem | Documented command | Result |
|---|---|---|
| bq-clickup-perf | `PERF_DRY_RUN=1 python3 bq_to_clickup_perf.py` | **FAIL as literally documented** — crashes: `FileNotFoundError: /tmp/clickup_pk`. Script defaults `TOKEN_FILE` to a Mac-era `/tmp` path (bq_to_clickup_perf.py:40); the real cron wrapper (`run_perf_writeback.sh`) always exports `TOKEN_FILE=~/.config/clickup/pk` first, so the live nightly job is unaffected. With `TOKEN_FILE=~/.config/clickup/pk` prefixed, it runs clean: "DRY RUN ... would write 5 fields to 175 tasks (875 field writes). No changes made." |
| launch-autofill | `AUTOFILL_LINT=1 python3 autofill.py` | PASS — printed a full lint table (em-dash, list-collapse-risk, naming warnings) across active tasks, exit 0. |
| fatigue-sentinel | `./run_sentinel.sh --dry-run` | PASS — printed "would push" preview for 1 decaying winner + Monday heartbeat, then sent the one documented real `[TEST]` min-priority ntfy push exactly as CLAUDE.md describes (RULES-permitted external write). |

**Verdict: 2/3 real as documented, 1/3 has a trivial doc gap (missing required env
var in the example command).** Fixed as an artifact, not live — see "Trivial fix" below.

## 3. karpathy-guidelines.SKILL.md artifact

- `~/fable-window/artifacts/karpathy-guidelines.SKILL.md`: frontmatter present and valid
  (`name`, `description`, `license`), body follows with 9 numbered sections.
- Grepped for placeholders (`TODO|TBD|PLACEHOLDER|{{|XXX|FIXME|lorem ipsum`): zero hits.
- Differs from the currently-installed live skill at `~/.claude/skills/karpathy-guidelines/SKILL.md`
  (that's the older v1) — expected and correct: this is task 42's proposed v2, shipped as an
  artifact pending approval (`karpathy-guidelines.CHANGES.md` sits alongside it), not yet
  installed. Not a defect.

**Verdict: PASS.**

## 4. Git hygiene — clean status + no existing source modified

**CCC (`feat/brain-tab`):**
- `git status --short` → one untracked entry: `.claude/`. Investigated: this is **two
  pre-existing registered git worktrees** (`.claude/worktrees/agent-ab2638dea56e0d7a2`,
  `agent-ad96d955180b69bd9`, ~42M, dated 2026-06-26 — 10 days before any fable-window
  task started). Not created by tasks 40-42, unrelated debris from an earlier agent-worktree
  run. Left untouched (deleting a registered worktree is a destructive op outside this
  task's scope). This is the only reason CCC isn't a fully clean tree.
- Diff-stat for the task-40 commit range (`c0a1081..8e6eab6`): `CLAUDE.md | 129 ++`,
  `scripts/verify-baseline.txt | 12 +`, `scripts/verify.sh | 50 +` — **3 new files only,
  191 insertions, 0 deletions.** No existing source file touched. `CLAUDE.md` history
  confirms it was net-new on this branch (no prior version existed to modify).

**~/systems (`main`):**
- `git status --short` → clean, nothing to report.
- Diff-stat for the task-41 commit range (`0b843ab..aacb134`): `CLAUDE.md | 265 ++` — **1
  new file, 265 insertions, 0 deletions.** No existing source touched. (The baseline commit
  `0b843ab` itself carries pending night-4 `autofill.py`/systemd-unit changes approved under
  a separate amendment 9/night-4 exception — not part of task 41's own diff, noted for
  completeness.)

**Verdict: systems clean; CCC has one pre-existing, out-of-scope untracked worktree pair —
not attributable to the dev-lane tasks, no existing source modified in either repo.**

## Trivial fix applied (as artifact, not live)

Per RULES rule 2, task 96 has no live-edit exception for `~/systems/CLAUDE.md` (only
tasks 40-42 did, and only for adding new files). Delivered per rule 3 instead:

- `artifacts/systems-CLAUDE.FIXED.md` — full replacement of `~/systems/CLAUDE.md` with the
  bq-clickup-perf dry-run command corrected to include `TOKEN_FILE=~/.config/clickup/pk`
  (lines 21 and 244).
- `artifacts/systems-CLAUDE.CHANGES.md` — what changed and why.

## Open questions

- Should `bq_to_clickup_perf.py:40`'s default `TOKEN_FILE` be changed from
  `/tmp/clickup_pk` to `~/.config/clickup/pk` at the source, so the bare command works
  without the env prefix? That's an edit to pre-existing source, out of this task's scope
  — flagging for a future task, not fixing here.
- The two orphaned CCC worktrees (`.claude/worktrees/agent-*`, 2026-06-26) are unrelated
  debris; recommend a separate cleanup task (`git worktree remove`) rather than folding it
  into dev-lane verification.
