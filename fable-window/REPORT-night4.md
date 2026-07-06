# Fable Window Night-4 Report — 2026-07-05

## 1. Executive summary

Tasks 30 through 38 (9 tasks, the night-4 live-exception batch under RULES rule 9) all ran, **exit=0 across the board**. Covered: applying the wiki canon-conflict sweep live to `~/brain` (16 files), an S27+ testing roadmap from a fresh BQ pull, a fable-window lessons distill, a Hermes orchestration skill upgrade (3 skills, artifact-only), a live security rebind (Option B), enabling two staged systemd timers, applying 15 trimmed skill descriptions live on the box, installing the launch-autofill lint replacement, and an independent verify pass (`VERIFY-night4.md`) that closed clean: 5/6 checks PASS, 1 PARTIAL (CCC's rebind, a known documented failure, not a new regression), zero mechanical fixes needed. Tasks 40 to 48 (the dev-lane and design/review batch) have not run yet — no logs, no `.done` files — and are the candidates for the last Fable night.

## 2. What is now LIVE vs artifact-only

### LIVE (already changed real state, verified against the running system just now)
- **`~/brain` wiki fixes (task 30):** 16 files edited in place (12 compliance-dangerous + 5 stale-stat findings). Snapshot-verified: `wiki-fix-baseline.sha256` 16/16 OK, spot-checked 5/17 findings match live content exactly.
- **Security Option B rebinds (task 34):** md-server now `100.107.26.69:8092` (tailnet-only, confirmed via `ss -tlnp` just now), camofox now `127.0.0.1:9377` (localhost-only, confirmed). **CCC is still `*:3000`** (all interfaces, confirmed live) — its rebind failed (Next 14.2.35 ignores `HOSTNAME` env) and was deliberately rolled back; this is an open item, not a hidden failure.
- **Systemd timers (task 35):** `atria-weekly.timer` and `fatigue-sentinel.timer` both confirmed `enabled`/`active (waiting)` just now (next fires Mon 07:30 and 08:30). **Gap:** no `_ledger.md` entry exists for this task — the enable action itself was never logged, only tasks 14/15's staging was. State is correct; paperwork is missing.
- **15 box skill descriptions (task 36):** confirmed live and correct just now (spot-checked `shameless-script/SKILL.md` frontmatter). Full list: system-control, clickup-task-creator, shameless-script, fleet-control, dr-script, landing-page-copy, gbrain-tag-audit, email-copy, firecrawl, micro-scripts, script-critique, interrogate, lt-marketplace-search, share-to-phone, firecrawl-interact. Known gap: 4 of the 15 backups (dr-script, landing-page-copy, email-copy, micro-scripts) hold post-edit content instead of true originals due to a self-inflicted script re-run bug during the task; live files themselves are unaffected and verified correct.
- **`~/systems/launch-autofill/autofill.py` (task 37):** confirmed live sha256 `ff6a8cdb...9020` matches the artifact exactly. Dry-run lint path confirmed read-only (zero POST/PUT/comment calls), 261 tasks scanned, 297 violations (54 fail/243 warn).

### Artifact-only (not yet applied anywhere — needs a deliberate apply step)
- **3 Hermes orchestration skills upgraded (task 33):** `hermes-routing-policy`, `delegate-to-claude`, `claude-heavy-lifting`, all bumped to v2.0.0. Confirmed just now: the live copies at `~/.hermes/skills/autonomous-ai-agents/*/SKILL.md` are still v1.0.0 and differ from the artifacts — Hermes has **not** picked these up yet. This is the box's own Hermes, separate from the Mac mirror question below.
- **`roadmap_S27plus.md`** (S27-S30 angle x format matrix) — recommendation doc, no apply step, action is briefing decisions.
- **`feedback_fable_window_lessons.md`** — shaped for promotion into the memory dir but deliberately not installed (out of RULES #2 scope); flags itself as pending a decision.
- **`karpathy-guidelines.SKILL.md` v2** — not yet produced (task 42, still queued).

## 3. Mac mirror checklist

Skills are per-machine real directories (not Syncthing-synced, per the night-3 report). Two new things need manual mirroring beyond the night-3 checklist (system-control, copy-craft skills, shameless-script, clickup-task-creator — see `REPORT.md` section 2 for those, unchanged).

### 3.1 Hermes orchestration skills (3, box-only path so far — apply to box's own Hermes first, then Mac if Mac runs its own Hermes instance)
```
for s in hermes-routing-policy delegate-to-claude claude-heavy-lifting; do
  cp ~/.hermes/skills/autonomous-ai-agents/$s/SKILL.md ~/.hermes/skills/autonomous-ai-agents/$s/SKILL.md.bak-2026-07-05
  cp ~/fable-window/artifacts/$s.SKILL.md ~/.hermes/skills/autonomous-ai-agents/$s/SKILL.md
done
```
Confirm before applying: box's own Hermes hasn't picked these up either (still v1.0.0 live) — this is a fresh apply, not a re-sync. If Tomas's Mac runs a separate Hermes instance with its own `~/.hermes/skills`, repeat the same copy there via `scp` from the box artifacts path.

### 3.2 Skill description trims (15 skills, box-applied already, per-machine so Mac needs its own pass)
```
# On Mac, for each of the 15 skills below, back up then replace only the description: field
# per artifacts/skill-descriptions.trimmed.md (do NOT copy the whole SKILL.md — only task 36's
# description-field edits are in scope; the 4 skills already covered by night-3's full-body
# replacement (dr-script, email-copy, landing-page-copy, micro-scripts) get the trim on top of
# whatever body version is live on Mac).
scp tomas@100.107.26.69:/home/tomas/fable-window/artifacts/skill-descriptions.trimmed.md ~/Downloads/
scp tomas@100.107.26.69:/home/tomas/fable-window/artifacts/skill-desc-apply.SUMMARY.md ~/Downloads/
# Then hand-apply the 15 description: field edits (system-control, clickup-task-creator,
# shameless-script, fleet-control, dr-script, landing-page-copy, gbrain-tag-audit, email-copy,
# firecrawl, micro-scripts, script-critique, interrogate, lt-marketplace-search, share-to-phone,
# firecrawl-interact), backing up each SKILL.md first.
```
Not on this checklist: wiki fixes (already synced, `~/brain` is the same canonical root reachable from both), security rebinds and systemd timers (box-only services), autofill.py (box-only cron host).

## 4. Open questions for Tomas

1. **Task 35 ledger gap** — the two systemd timers are live and correct, but no `_ledger.md` entry exists for the enable action. Recommend back-filling one with the real authorization/timestamp rather than fabricating it here.
2. **CCC still LAN-exposed on port 3000** — Option B's rebind failed (Next 14.2.35 ignores `HOSTNAME` env). Fix is `next dev -H 127.0.0.1` in the dev script, or fold CCC into an Option A firewall drop instead. Recommend deciding before the box goes back to unattended cron-only operation.
3. **4 non-pristine skill-description backups** (dr-script, landing-page-copy, email-copy, micro-scripts) — live content is verified correct, but their `.bak-2026-07-05` files hold post-edit content instead of true originals (self-inflicted script bug during task 36). Zero practical risk now; only matters if a full rollback is ever needed.
4. **Hermes orchestration skills v2** — ready in artifacts, not applied anywhere yet (box's own Hermes is still on v1.0.0). Say the word to apply the box copy; separately confirm whether Mac runs its own Hermes instance needing the same treatment.
5. **feedback_fable_window_lessons.md promotion** — shaped for direct install into the memory dir (box+Mac via Syncthing), not done per RULES #2. Confirm if you want it promoted.
6. **Em-dash policy scope** — still open since night-3 (carried forward, not re-litigated here): are SKILL.md/operational docs exempt from RULES #5's em-dash ban, or should a real strip pass run? Affects several artifacts from tonight too (hermes skills, roadmap).
7. **Standing item from night-3, still unresolved:** SH-9428 remains live and scaling despite the 2026-06-22 KILL call (surfaced again in tonight's roadmap task as a do-not-test flag) — ops decision, not a testing lane.

## 5. Last Fable night (2026-07-06) candidates

Fable 5's window closes 2026-07-07, so tomorrow night is the last full run before that. Tasks 40-48 (9 tasks) are queued and untouched — no logs, no `.done` files. Given a single ~8-10h overnight budget, ranked by leverage:

1. **Task 40 (CCC dev map) + Task 41 (systems dev map)** — highest leverage, lowest risk: these produce `CLAUDE.md` onboarding docs (dev-lane exception, additive-only, git-committed before/after) so any future session becomes instantly effective in both repos. Do these first; everything else benefits from them existing.
2. **Task 43 (CCC lanes bug diagnosis)** — cheap, diagnosis-only, directly unblocks the opportunity-scan's #1-ranked automation idea (Monday Brief Conveyor) once task 40's branch map exists to inform it.
3. **Task 42 (karpathy-guidelines v2)** — artifact-only, self-contained, meta-value for every future task in this window and beyond.
4. **Task 45 (eval factory)** — builds on tonight's own compliance-eval lessons; has a hard self-check (scorer must hit 1.0/1.0 on its own gold) so it either finishes clean or fails loud, good fit for a headless run.
5. **Task 44 (visual winner canon)** — valuable but the highest wall-clock risk: downloading and reading ~30 images is slow and network-dependent; schedule it early in the night with room to degrade gracefully (RULES rule 6) if attachments are auth-walled.
6. **Task 46 (research distill) and Task 47 (iteration-brief design)** — medium value, no external dependencies, good filler if time remains after 1-5.
7. **Task 48 (agentic-os review)** — lowest urgency (a review of a design doc, not a working system); do last or defer past the window close if time runs out.

If the full 9 cannot fit, cut from the bottom of this list (48, then 46/47), never from the top — 40/41 are foundational and 43 is blocking a real automation decision.
