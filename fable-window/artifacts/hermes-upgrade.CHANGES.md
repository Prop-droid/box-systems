# Hermes orchestration skill upgrades - CHANGES (2026-07-05)

Rewrites of the 3 Hermes orchestration skills (hermes-routing-policy, delegate-to-claude, claude-heavy-lifting), following the copy-craft upgrade conventions: ordered kill-criteria checklists, failure-modes sections (mistake then correction), tightened trigger descriptions with explicit negative routing between the sibling skills. All three bumped to version 2.0.0. NOT installed - Hermes reads `~/.hermes/skills/autonomous-ai-agents/*` live; apply in the morning by replacing each `SKILL.md`.

Install targets:
- `~/.hermes/skills/autonomous-ai-agents/hermes-routing-policy/SKILL.md`
- `~/.hermes/skills/autonomous-ai-agents/delegate-to-claude/SKILL.md`
- `~/.hermes/skills/autonomous-ai-agents/claude-heavy-lifting/SKILL.md`
(the `~/.claude/skills/*` paths are symlinks into these; one write covers both consumers)

## Cross-cutting (all three)

- **Usage-window gate added as step 0.** The load-bearing new fact: Hermes's own model calls (gpt-5.5 via Codex, Gemini fallback) do NOT draw the Claude subscription cap; every `claude` CLI delegation draws the SAME 5h window Tomas's interactive sessions use. Before any delegation, read `~/.claude/usage-window.json` (pct / block_end / updated) and check `~/.claude/PAUSE_CLAUDE_BG`. Thresholds: <70 normal, 70-89 cheap presets + defer batch, >=90 daytime (08:00-23:00 Vilnius) = no new heavy delegations, PAUSE flag = queue unless Tomas says now, stale `updated` (>15 min) = treat as unknown, night = burn freely. Heavy runs get a stricter >=80 daytime cutoff (claude-heavy-lifting).
- **Hardcoded reset times removed.** Old delegate-to-claude said "resets at 00:30 Europe/Vilnius" (box CLAUDE.md says 19:00; live JSON currently shows block_end at midnight UTC). All three now say: read `block_end`, never assume a fixed hour.
- **"Weekly cap" framing replaced** with the 5h-window reality metered by usage-guard.
- **Verify-target handoffs made mandatory** (per feedback_define_verification_target): every delegation packet names the expected output + verify command, tells Claude to iterate until it passes, and Hermes re-runs the verify itself after return. Research tasks name the deliverable shape instead. "No verifiable target = say so, don't fake it" (anti verification-theater) included.
- **CLARIFICATION_REQUIRED folded into all three.** Was only in delegate-to-claude; heavy-lifting had nothing (Hermes could silently guess on the most expensive runs). Verbatim block stays in delegate-to-claude; the other two require and reference it. Own-line detection rule kept.
- **Kill-criteria checklists** replace prose guidance: routing checklist (routing-policy, 6 steps), pre-flight checklist (delegate-to-claude, 6 steps), run-sizing criteria (heavy-lifting, per-choice KILLs).
- **Failure-modes sections added** to all three, absorbing the old Pitfalls/Anti-patterns content plus the new gate/verify failure modes.
- **Trigger descriptions tightened** with explicit routing: routing-policy = WHEN, delegate-to-claude = HOW, claude-heavy-lifting = sizing heavy runs only, with NOT-for lists in each description so the right one fires.
- **Model pins updated.** `claude-sonnet-4-6` replaced by `claude-sonnet-5` as the worker default; the "Opus 4.7 terminal default" pin dropped in favor of "never downgrade Tomas's terminal default" (version-proof).
- **Em/en dashes removed** from all three files for consistency with prior fable-window artifacts.

## hermes-routing-policy

- New "Roles and billing reality" section: which executor bills where, Claude window = the shared scarce resource.
- New "usage-window gate" section with the JSON shape and full threshold table; gate wired into tier 2, the quick decision flow, the checklist (step 0), edge cases (gate-red-but-urgent = one-line ask to Tomas), and telemetry (`usage_pct_at_launch` field added).
- Scope line added: policy governs turns arriving AT Hermes; system-wide Claude Code stays the primary worker (per feedback_claude_orchestrator_hermes_fixer) - prevents re-reading this skill as "Hermes is the brain".
- Ollama tier renamed to "cheap tier" and corrected to the box reality: Hermes delegation model is Gemini 3.5 Flash (`delegation:` in `~/.hermes/config.yaml`); Ollama is NOT installed on the box, kept only as "where actually installed".
- Tier rules, single-executor rule, cost discipline, edge cases, telemetry, decision flow all kept; anti-patterns converted to failure modes with two new ones (cap-blind delegation, hardcoded reset times).

## delegate-to-claude

- Pre-flight checklist (new, 6 ordered KILLs): usage gate, resume-or-new, bounded command, verify target, payload trim, clarification block.
- New "Verify-target handoff" section: expected output + verify command in every packet, cheap verifiers first, Hermes re-verifies on return, error_max_turns = incomplete handoff (promoted from a buried pitfall to a numbered post-processing rule).
- Task packet template gains a "Verify target" slot and a "Verification: command run + result" line in the output format; note added to keep static blocks byte-identical for prompt caching.
- Session-resumption section rewritten around `block_end` (was hardcoded 00:30).
- Helper-scripts section corrected to reality: `~/.hermes/scripts/` does NOT exist on the box (verified 2026-07-05); claude_delegate.py / ollama_router.py / claude_tmux_sweeper.py marked Mac-era "if present", with the inline-command fallback stated. The 2026-05-05 usage-audit reference file pointer dropped from the body (file still exists in references/ if wanted).
- Presets consolidated into one list (cheap_read / cheap_research / read_only / code_review / edit_with_approval / long_tmux) instead of being split across two sections; command patterns gain explicit `--model claude-sonnet-5`.
- All 12 pitfalls preserved as failure modes (max-turns/allowedTools, dangerously-skip-permissions, tmux hygiene, guessed session ids, cost-field caveat, clarification false positives, Do-NOT-retry discipline); the pipe-to-interpreter scanner note dropped as helper-script-specific (helpers absent).

## claude-heavy-lifting

- Repositioned from "third overlapping copy of the routing rules" to the heavy-run sizing profile; the old skill duplicated routing tiers, packet template, and command patterns already owned by the other two. Now: what qualifies as heavy, the stricter gate, run sizing, heavy packet additions, post-return verification.
- Stricter gate for heavy runs: >=80% daytime = queue (vs the general >=90), plus a block_end-proximity check (don't start a 15-turn run 10 min before reset).
- Run sizing given per-choice kill criteria: mode (print vs tmux), turns (5/8/15-20, plus "budget too small for the verify loop guarantees error_max_turns"), effort (max only on explicit ask), model (Sonnet default, Opus = explicit escalation), tools, billing, workdir.
- CLARIFICATION_REQUIRED requirement added (was entirely missing here).
- Verify target made mandatory for heavy packets; "Verification:" line added to the final response style so Tomas sees what was actually checked.
- Kept: Hermes-stays-on-Codex core rule, executive-summary-first output contract, Max-login billing guidance, secrets redaction, final response shape.

## Open questions

1. **Helper scripts absent on the box (verified).** `~/.hermes/scripts/` does not exist; the delegate flow currently has no session ledger or dry-run tooling on the box. Either port claude_delegate.py from the Mac or accept inline commands + working-notes ledger as the box contract. The rewrite supports both.
2. **Threshold tuning.** The 70/80/90 pct tiers and the 15-min staleness window are judgment calls consistent with usage-guard's 90% trip; tune after a week of telemetry (`usage_pct_at_launch`).
3. **Enforcement is prompt-level only.** Hermes reads these skills as text; nothing hard-stops a gate-blind `claude -p`. A cheap hard enforcement: route Hermes delegations through the `/opt/agentbox/bin/claude-max` wrapper (already PAUSE-flag-aware) instead of bare `claude`.
4. **AppleDouble litter.** `._SKILL.md` / `._references` files sit in all three skill dirs (Syncthing/Mac artifacts); harmless but deletable at install time.
5. **references/ dir.** delegate-to-claude keeps `references/usage-optimization-and-approval-2026-05-05.md`; still valid history, no action needed.
