# Fable Window Night-3 Report — 2026-07-04

## 1. Executive summary

Night-3 core tasks (20-26) **all exit=0**, VERIFY-night3.md re-checked all 7 of them live and found
only 1 trivial fix needed. Task 27 (a separate, later-queued A/B clean-run, not in the night-3 verify
scope) **never completed** — hit the Claude usage limit 16 times over ~8h and gave up at 22:28; no
artifact, nothing to apply from it.

Covered: winner-pattern canon v2 (subtask mine + fresh BQ reweight), a wiki canon-conflict sweep (20
findings, read-only), a live authorized compliance-eval policy patch (scorer 1.0/1.0), 3 extracted
playbooks, staged memory/CLAUDE.md/skill-description trims, and staged (not applied) security
remediation (nft + service patches). Everything except task 22's pre-authorized live patch is
artifacts-only, per RULES #2.

## 2. What passed / failed

**Passed, independently re-verified by VERIFY-night3.md:**
- Task 20 `winner_patterns_v2.md` + SOURCES — reweighted with 4 live BQ queries + 635 mined subtasks; live memory file untouched.
- Task 21 `wiki-conflict-sweep.md` — 131 files swept, 20 findings (12 compliance-danger / 5 stale-stat / 3 tone), tier counts match ledger exactly, no wiki files touched.
- Task 22 `policy-gap-close` — **LIVE** commit to `~/systems/compliance-eval` (authorized exception, rule 8): `test_scorer.py` independently re-run, **precision=recall=1.000**.
- Task 23 playbooks ×3 (image-test batch, launch-fill, overnight harness) — field UUIDs spot-checked verbatim against source, zero em dashes.
- Task 24 memory-trim staging — `MEMORY.md.trimmed` link parity **133/133** diffed clean; `CLAUDE.md.box.trimmed` reset-time and 10 load-bearing facts confirmed matching live.
- Task 25 `security-stage/` — both `.nft` files parse (`sudo nft -c`), both `.patch` files apply clean (`git apply --check`) against live targets, `.service` files verified, nothing loaded/installed live.
- Task 26 VERIFY-night3 itself — 1 stray em dash fixed in `context-audit-staged.CHANGES.md` (mechanical, in-place).

**Flagged, not fixed (recurring policy question, same as night-2):**
- `wiki-conflict-sweep.md` — 71 em/en dashes in author prose.
- `policy-gap-close.SUMMARY.md` — 14 em/en dashes in author prose.

**Failed:**
- Task 27 `eval-ab-clean` — retried every 30min from 14:03 to 22:28 (16 tries), all blocked on session limit, driver marked `LIMIT-GAVE-UP`. No results produced. Not part of VERIFY-night3.md's scope.

## 3. Apply checklist (risk-ordered, backup-first — everything below is staged, nothing is live yet except task 22)

1. **Zero risk — already live, nothing to do.** Confirm if you want: `cd ~/systems/compliance-eval && python3 test_scorer.py`
2. **Low risk, box+Mac via Syncthing** — promote `MEMORY.md.trimmed` (133/133 link parity verified):
   `cp ~/.claude/projects/-home-tomas/memory/MEMORY.md{,.bak-2026-07-04} && cp ~/fable-window/artifacts/MEMORY.md.trimmed ~/.claude/projects/-home-tomas/memory/MEMORY.md`
3. **Low risk, box-only** (do not copy to Mac — different file) — promote `CLAUDE.md.box.trimmed`:
   `cp ~/.claude/CLAUDE.md{,.bak-2026-07-04} && cp ~/fable-window/artifacts/CLAUDE.md.box.trimmed ~/.claude/CLAUDE.md`
4. **Low-medium risk, box+Mac via Syncthing, judgment call open** — promote `winner_patterns_v2.md` over live `feedback_winner_patterns_2026H1.md`:
   `cp ~/.claude/projects/-home-tomas/memory/feedback_winner_patterns_2026H1.md{,.bak-2026-07-04} && cp ~/fable-window/artifacts/winner_patterns_v2.md ~/.claude/projects/-home-tomas/memory/feedback_winner_patterns_2026H1.md`
   (resolve open question 2 below first)
5. **Medium risk, per-machine (skills don't sync)** — `skill-descriptions.trimmed.md`: hand-paste 15 `description:` fields into each skill's SKILL.md, on box then Mac; verify routing still fires after.
6. **Medium-high risk, box-only, real network/service change** — `security-stage/`: `cd ~/fable-window/artifacts/security-stage && sudo bash optionA-apply.sh` (rollback: `sudo bash optionA-rollback.sh`); Option B per-service patches (md-server/CCC/camofox only — **not** tablet-dash, it's LAN-only) are separate, read `README.md`'s blast-radius table first.

Not on the checklist: `wiki-conflict-sweep.md` findings (20 wiki edits, judgment calls not a script) and the 3 playbooks (reference docs, no live surface — file them wherever you'll read them next).

## 4. Open questions

1. Em-dash policy: does RULES #5 exempt internal audit/report/playbook prose, or should `wiki-conflict-sweep.md` (71) and `policy-gap-close.SUMMARY.md` (14) get a real per-sentence editing pass?
2. `winner_patterns_v2` promotion: the abandoned-subtask semantics are mixed (killed-after-launch vs never-launched) — does that change how you read the keep-rate figures before you promote it?
3. Task 27 (shameless-script A/B clean run) never ran — re-queue next window, or drop?
4. Security stage: Option A only, A+B, or hold entirely? Persisting Option A across reboot needs a further systemd unit, not staged here.
5. Memory-trim savings (~1,550-1,820 tok total across MEMORY.md/CLAUDE.md/skill-descriptions) — accept as scoped, or push for a deeper cut (would mean dropping some load-bearing IDs)?
