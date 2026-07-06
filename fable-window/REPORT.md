# Fable Window Morning Report — 2026-07-04

## 1. Executive summary

17/17 tasks ran, **exit=0 across the board**, no failures, nothing to tail. Overnight run (2026-07-02 through 2026-07-04) covered: 7 SKILL.md rewrites/new skills, a memory canon distill, compliance-eval expansion + a LIVE authorized policy patch, a context/token audit, a full verify pass, a security sweep, an opportunity scan, a CCC UX pass, an autofill convention linter, and two new staged (not enabled) crons.

**Passed verification (task 08, VERIFY.md):**
- All 7 SKILL.md files: frontmatter now parses clean (4 had a real YAML bug — invalid plain-scalar `word: word` in `description:` — fixed mechanically).
- compliance-eval new cases (20/20) + gold labels: clean, full coverage.
- `feedback_winner_patterns_2026H1.md` frontmatter: valid.
- Task 06 system-control install: byte-identical, confirmed live.

**Failed / flagged, not fixed (needs your call):**
- **Em dashes:** all 7 SKILL.md files still contain em dashes (21–57 each, ~276 total) — fails RULES #5 read literally. Three ledger entries argue RULES #5 only scopes to copy-facing creative text, not skill docs, so they were deliberately kept. Verify pass flagged this as a genuine policy conflict, not a typo — **needs your decision**, see open questions.
- **`feedback_winner_patterns_2026H1.md`** is already live in your memory dir (and Syncthing-synced to Mac already — no action needed there) — flagged only because RULES #2 didn't authorize that promotion; verify it was intentional.

**Live/authorized writes already applied (not pending):**
- Task 07b patched `~/systems/compliance-eval` live and committed (baseline `ebda053` → patch `73da066`) — Tomas pre-authorized this exception. `test_scorer.py` precision=recall=1.0/15, exit 0.
- Task 06 installed `~/.claude/skills/system-control/SKILL.md` live on the box (new skill, didn't exist before).
- Task 15 wrote a new dated Atria snapshot under `~/brain/projects/2026-06/competitor-ads-scrape/atria/` (additive, authorized).

**Box-only, no Mac action needed:** security sweep (14), opportunity scan (11), CCC UX pass (12), autofill lint (13), fatigue-sentinel (14) and atria-weekly (15) staging — these are analysis/cron scaffolding tied to box-hosted services (BQ, ClickUp, CCC dev server, systemd). Nothing here runs on Mac.

## 2. APPLY CHECKLIST (run on Mac, pulling from box at `tomas@100.107.26.69`)

Only the **Claude Code skills** need mirroring to Mac — skills are per-machine real dirs (not Syncthing-synced, confirmed). Memory files already sync automatically; `~/systems` crons are box-only. Ordered lowest-risk (new install) → highest-risk (replaces a skill with real-world side effects).

### 2.1 New install — system-control (didn't exist before; no backup needed, but check first)
```
ssh mac 'test -d ~/.claude/skills/system-control && echo "EXISTS - stop, this is not new on Mac" || echo "confirmed missing, safe to install"'
mkdir -p ~/.claude/skills/system-control
scp tomas@100.107.26.69:/home/tomas/fable-window/artifacts/system-control.SKILL.md ~/.claude/skills/system-control/SKILL.md
```

### 2.2 Replacements — generic copy-craft skills (used across all brands, not Shameless-critical)
```
for s in dr-script email-copy landing-page-copy micro-scripts; do
  cp ~/.claude/skills/$s/SKILL.md ~/.claude/skills/$s/SKILL.md.bak-2026-07-04
  scp tomas@100.107.26.69:/home/tomas/fable-window/artifacts/$s.SKILL.md ~/.claude/skills/$s/SKILL.md
done
```

### 2.3 Replacement — shameless-script (daily-use, brand-critical)
```
cp ~/.claude/skills/shameless-script/SKILL.md ~/.claude/skills/shameless-script/SKILL.md.bak-2026-07-04
scp tomas@100.107.26.69:/home/tomas/fable-window/artifacts/shameless-script.SKILL.md ~/.claude/skills/shameless-script/SKILL.md
```

### 2.4 Replacement — clickup-task-creator (highest blast radius: writes real ClickUp tasks)
```
cp ~/.claude/skills/clickup-task-creator/SKILL.md ~/.claude/skills/clickup-task-creator/SKILL.md.bak-2026-07-04
scp tomas@100.107.26.69:/home/tomas/fable-window/artifacts/clickup-task-creator.SKILL.md ~/.claude/skills/clickup-task-creator/SKILL.md
```
Sanity-check after: create one throwaway/dry-run task before trusting it on a real batch (per the ledger's own open questions on dropdown-format and userid assumptions).

### Not on this checklist, and why
- `feedback_winner_patterns_2026H1.md` — already live + Syncthing-synced to Mac, nothing to do.
- `CLAUDE.md.replacement.md` — trimmed version of the **box's own** CLAUDE.md ("tailored for the box"). Do not paste onto Mac's CLAUDE.md, they're different files for different roles. Applies (if you want it) only on the box itself.
- compliance-eval new_cases/new_gold/HOWTO, autofill.py.replacement, fatigue-sentinel/*, atria-weekly/* — all target `~/systems/` (box-only cron host, systemd not launchd). Only relevant on Mac if you maintain a separate clone of `Prop-droid/box-systems` there — confirm before treating this as a to-do.
- security-sweep.md, opportunity-scan.md, ccc-ux-pass.md — findings/recommendations, not artifacts. Action items live on the box (firewall rules, CCC dev-mode, etc.).

## 3. Open questions for Tomas

1. **Em-dash scope in skill docs:** keep the "operational/skill docs are exempt from RULES #5" reading (drop it from future verify passes), or should I run a real editing pass to strip all ~276 em dashes from the 7 SKILL.md files? Affects clickup-task-creator, system-control, context-audit too (same call made there).
2. **`feedback_winner_patterns_2026H1.md` promotion** — confirm the 2026-07-02 live promotion into memory was intentional (it's outside this window's RULES #2 exception, just noting it, not touching it).
3. **compliance-eval policy.json**: still lacks fixtures/patterns proposed in task 04's new cases (12 of 20 marked `policy_gap`); a follow-up pass could ship policy.json + matching gold fixtures.
4. **Security sweep top asks** (from security-sweep.md): pick a firewall approach — default-drop LAN nft rule vs. rebinding md-server/CCC/camofox/tablet-dash to 127.0.0.1/tailnet-only — and decide on SSH key passphrases (mac/nobara/github-personal keys are all unencrypted).
5. **CCC UX pass**: is the lanes→brief pipeline (`suggestedBrief` empty on all 12 lanes) a real bug or unshipped V2 scope? Blocks the opportunity-scan's #1-ranked automation idea (Monday Brief Conveyor).
6. **fatigue-sentinel / atria-weekly**: both are staged but not enabled (no systemd timer registered, watchdog not updated). Say the word if you want either turned on for real.
7. **Task 06/skill dropdown/userid assumptions** in clickup-task-creator (orderindex-first vs UUID-first for dropdowns; Anastasiia userid `81523938`) — confirm against a live task before your next batch.

## Night-3 addendum (2026-07-04)
Tasks 20-26 all exit=0, VERIFY-night3.md re-checked all 7 live (scorer 1.0/1.0, nft/patches parse/apply clean, MEMORY.md link parity 133/133) — 1 trivial em-dash fix applied, 2 files still flag the recurring em-dash policy question. Task 27 (eval-ab-clean, separate from the verify scope) never completed — hit the session usage limit 16x over ~8h and gave up; re-queue after reset. Full detail: `REPORT-night3.md`.

## Night-4 addendum (2026-07-05)
Tasks 30-38 all exit=0, VERIFY-night4.md re-checked all night-4 live exceptions (wiki fixes 16/16 sha256 OK, both systemd timers enabled+active, 15 skill-description edits clean, autofill script sha256-matched) — 5/6 checks PASS clean, 1 PARTIAL (CCC's security rebind failed and was rolled back, a known documented gap, not a new regression). Tasks 40-48 never started (no logs/`.done` files) — queued for the last Fable night, 2026-07-06, ranked in `REPORT-night4.md` section 5. Full detail: `REPORT-night4.md`.
