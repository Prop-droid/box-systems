---
name: claude-heavy-lifting
description: Shape and run HEAVY Claude Code delegations from Hermes - deep research, large-context synthesis, codebase-scale analysis, multi-file implementation, long-form planning. Defines run sizing (mode, turns, effort, model), heavy-specific packet requirements, and post-return verification. Fires on "deep research", "heavy lifting", "use Claude as the brain", "full analysis", "analyze this entire repo", "ultrathink", "give me a full strategic breakdown", and requests to push big work off ChatGPT/Codex. Does NOT fire for quick inspections or bounded lookups (delegate-to-claude cheap presets), for deciding where a turn runs (hermes-routing-policy), or as a license to default all work to Claude.
version: 2.0.0
author: Hermes Agent + Tomas workflow
metadata:
  hermes:
    tags: [claude, delegation, research, analysis, orchestration, heavy-lifting, usage-window]
    related_skills: [claude-code, delegate-to-claude, hermes-agent, hermes-routing-policy]
---

# Claude Heavy Lifting Workflow

For tasks that are token-heavy, analytically complex, research-heavy, or span large context: Hermes stays the router, messenger, verifier, and final communicator; Claude Code does the reasoning pass through Tomas's Claude Max terminal login. Hermes remains on Codex for conversational tool-calling reliability; do not force Hermes off it.

Division of labor across the three skills: `hermes-routing-policy` decides WHEN a turn delegates at all; `delegate-to-claude` owns the mechanics (checklist, presets, packet template, clarification handoff); THIS skill sizes and shapes the run once the task is confirmed heavy.

## What qualifies as heavy

1. Deep analytical research or strategic synthesis.
2. Long-context document or codebase reviews.
3. Complex implementation plans or architecture decisions.
4. Multi-file coding/refactoring where Claude inspects and edits directly.
5. Tasks that would consume many Hermes turns or tokens.
6. Explicit user asks: "deep research", "heavy lifting", "use Claude as the brain", "full analysis", "ultrathink", "avoid ChatGPT/OpenAI usage" on a big task.

NOT heavy: status checks, single-file reads, bounded web lookups, quick config inspections. Those go through `delegate-to-claude` cheap presets (2-3 turns) or stay in Hermes.

## Usage-window gate - stricter for heavy runs

A heavy run is the single biggest draw Hermes can place on Tomas's shared 5h Claude window (his interactive sessions bill to the same window; Hermes's own Codex/Gemini calls do not). Before launching, read `~/.claude/usage-window.json` and check `~/.claude/PAUSE_CLAUDE_BG`:

- **pct >= 80 during 08:00-23:00 Europe/Vilnius** - do NOT start a new heavy run (note: stricter than the general >= 90 delegation gate). Queue it for `block_end` and tell Tomas in one line when it will run.
- **PAUSE flag present** - background Claude is paused; queue unless Tomas explicitly says run this now.
- **`updated` stale (> ~15 min)** - treat pct as unknown; probe with a cheap preset or wait.
- **Approaching `block_end`** - a 15-turn run started 10 minutes before reset will stall mid-flight; either wait for the fresh window or accept the resume cost knowingly.
- **Night (23:00-08:00)** - burn freely by design.

Never hardcode reset hours; `block_end` is the only truth.

## Run sizing - each choice has a kill criterion

- **Mode.** Print mode (`claude -p --output-format json`) for one-shot heavy tasks. tmux only for genuinely interactive multi-stage work needing monitoring or follow-ups. KILL: tmux for a task print mode finishes in one pass; unnamed or unswept tmux sessions.
- **Turns.** `--max-turns 5` for analysis/research, 8 for repo review, 15-20 for implementation. KILL: any command without `--max-turns`; a turn budget obviously too small for the verify loop (that guarantees an `error_max_turns` half-finished handoff).
- **Effort.** `--effort high` for heavy reasoning. `max` only when Tomas explicitly asks for maximum reasoning. KILL: `max` as a silent default.
- **Model.** Sonnet (`claude-sonnet-5`) by default even for heavy runs; Opus only on explicit ask or when the task demonstrably needs it. KILL: Opus as the reflexive "it's heavy" choice.
- **Tools.** Narrowest preset that fits: `Read,WebSearch,WebFetch` for research; add `Bash/Edit/Write` only for implementation with explicit scope from Tomas. KILL: any command without `--allowedTools`.
- **Billing.** Max terminal login, not API keys, unless Tomas explicitly requests API billing (then use `--max-budget-usd`). `total_cost_usd` under Max login is an estimate.
- **workdir.** Always set when the task touches a project.

## Heavy packet requirements

Use the `delegate-to-claude` packet template (static protocol blocks byte-identical for prompt caching). Heavy runs additionally require:

1. **Verify target, always.** Implementation: expected output + verify command, with "iterate until it passes" in the packet. Research/synthesis: the deliverable shape - sections, questions answered, sources cited, facts separated from assumptions. A heavy run without a target is an expensive one-shot blind.
2. **Executive answer first.** Concise answer up top, detailed reasoning/sources after, recommended next actions at the end.
3. **Gaps stated.** If information is missing, Claude says what is missing and how to get it rather than padding.
4. **CLARIFICATION_REQUIRED protocol embedded** (verbatim block in `delegate-to-claude`). Hermes relays Claude's question to Tomas and resumes with the answer; it never guesses. Long heavy runs are exactly where a wrong guessed assumption compounds most.
5. **Safety block.** No secrets, no commit/push/deploy/schedule without explicit ask; edits stop at shown-and-verified.

## After Claude returns

1. Parse JSON; capture `session_id`, `num_turns`, `subtype` in the thread ledger.
2. `error_max_turns` = incomplete handoff. Inspect git status/diff, finish or revert partial work (resume the SAME session), re-verify. Never report it as done.
3. Run the verify command yourself; for edits, inspect the diff and run tests. Independently spot-check critical claims where practical.
4. Compress the result through the cheap tier before it enters Hermes context; never paste multi-page raw output back in.
5. Reply to Tomas in the shape below.

## Failure modes - do not repeat

- **Everything-to-Claude.** Routing all work here just shifts the bottleneck onto Tomas's 5h window. Heavy means heavy; the cheap presets and Hermes-direct exist for the rest.
- **Gate-blind launches.** Starting a 20-turn Opus run at 85% daytime usage, starving Tomas's own session. Gate first, every time.
- **Opus reflex.** "It's heavy, so Opus." Sonnet handles most heavy runs; Opus is an explicit escalation.
- **One-shot blind.** No verify target, then trusting the summary. Name the target, make Claude loop, re-verify on return.
- **error_max_turns as success.** Partial edits shipped as done; this has burned real work before. Inspect and finish.
- **Fresh-session heavy reruns.** Restarting a stalled heavy run from scratch after a window reset instead of `--resume` from `block_end`.
- **Hermes re-analysis.** Re-reasoning over Claude's output in GPT "to check it" instead of running the verify command; doubles spend without adding verification.
- **Raw-dump re-entry.** Multi-page Claude output pasted into Hermes context uncompressed.
- **Secrets in packets.** Forwarding `.env`, keys, tokens; redact unless strictly necessary and requested.

## Final response style

```text
I delegated the heavy analysis to Claude Code, then verified/summarized the result.

Bottom line: ...
Key findings: ...
Verification: <command/check run and its result>
Recommended next step: ...
```

Concise unless Tomas asks for the full output.
