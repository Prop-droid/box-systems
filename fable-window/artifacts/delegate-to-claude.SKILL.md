---
name: delegate-to-claude
description: HOW to hand a task to Claude Code once routing has picked delegation - pre-flight checklist with the usage-window gate, safety presets, command patterns, task packet with a mandatory verify target, CLARIFICATION_REQUIRED handoff back to Tomas, session resumption, and post-return verification. Fires on "use Claude", "ask Claude", "pass to Claude", "delegate this", "use Claude skills/superpowers", "conserve GPT/Codex", and on any tier-2 routing decision. Does NOT decide WHEN to route (use hermes-routing-policy) or how to size deep-research / large-context runs (use claude-heavy-lifting).
version: 2.0.0
author: Hermes Agent + Tomas workflow
metadata:
  hermes:
    tags: [claude, delegation, whatsapp, orchestration, superpowers, clarification, verify-target]
    related_skills: [claude-code, claude-heavy-lifting, hermes-agent, hermes-routing-policy]
---

# Delegate to Claude Code

Hermes is the orchestrator, messenger, safety gate, and final summarizer. Claude Code is the heavy-lift worker, reached through Tomas's Claude Max terminal login. Do not make Hermes do large reasoning or context-heavy work Claude Code can own.

WHEN to delegate lives in `hermes-routing-policy` (tiers, single-executor rule, cost discipline). Sizing heavy runs lives in `claude-heavy-lifting`. This skill is the mechanics.

## Pre-flight checklist - ordered, each step has a kill criterion

Run before every delegation. A failed step means fix it before launching, not launch with a caveat.

0. **Usage-window gate.** Read `~/.claude/usage-window.json` (`pct`, `block_end`, `updated`) and check for `~/.claude/PAUSE_CLAUDE_BG`. Claude delegations draw Tomas's shared 5h subscription window; Hermes's own model calls do not. KILL: launching at >= 90% during 08:00-23:00 Vilnius, launching with the PAUSE flag present, or treating stale data (`updated` older than ~15 min) as green. Full thresholds in `hermes-routing-policy`.
1. **Resume or new?** Check the thread ledger for an existing `session_id`. KILL: a fresh session when the thread already has one; `--resume` keeps the prompt cache warm and the context intact.
2. **Bounded command.** Pick a preset. KILL: any `claude -p` missing `--max-turns` or `--allowedTools`. Both, every time, no exceptions.
3. **Verify target in the packet.** KILL: an implementation packet without a named expected output AND a verify command Claude can loop against. Analysis/research packets name the expected deliverable shape instead (see next section).
4. **Payload trimmed.** KILL: Hermes's own reasoning, commentary, or scratchpad forwarded inside the packet. Claude gets the user's content and minimal context, nothing else.
5. **Clarification protocol embedded.** KILL: a packet without the CLARIFICATION_REQUIRED block; Hermes must never guess answers to Claude's substantive questions.

## Verify-target handoff

A delegation without a verification target is a one-shot blind. For every task, name in the packet:

- **The expected output.** A passing test, a file with specific properties, a diff against a known baseline, an expected data shape, a clean `py_compile`/`tsc`/lint run.
- **The verify command.** Bake it in: "implement X, then run `<cmd>`, iterate until it passes." Cheap verifiers first (lint, type-check, single test) before expensive ones (full suite, browser).
- **For analysis/research tasks:** the deliverable shape (sections, questions answered, sources cited) is the target; Claude self-checks against it before returning.

If a task has no verifiable target, say so in the packet and have Claude state its confidence and gaps rather than faking a loop (verification theater). After Claude returns, Hermes re-runs the verify command itself before reporting done: readback, diff, or test. Claude saying "done" is a claim, not a verification.

## Mandatory Claude skill/superpower instruction

Every packet MUST tell Claude to:

1. Use all relevant installed Claude Code skills, plugins, agents, and superpowers.
2. Prefer superpowers workflows where relevant: planning, parallel agents, systematic debugging, code review, TDD, execution, skill creation.
3. Load relevant project/global instructions: `CLAUDE.md`, `.claude/skills`, plugin skills, custom agents.
4. Recommend creating a missing skill (or use skill-creator) when the task reveals one should exist.

## Clarification handoff rule

Hermes must not guess answers to Claude's substantive follow-up questions. Every packet requires this protocol:

```text
If you need input from Tomas before proceeding, STOP and return exactly:
CLARIFICATION_REQUIRED
Question: <the question Hermes should ask Tomas>
Options: <optional choices, if helpful>
Why needed: <brief reason>
Do not continue past this point until Hermes provides Tomas's answer.
```

When Claude returns it, Hermes must:
1. Ask Tomas the question over the current channel, preserving Claude's wording.
2. After Tomas answers, resume Claude (`--resume <session_id>`) with the answer.
3. Never invent missing product, code, business, credential, or approval details.

Detection: trigger ONLY when `CLARIFICATION_REQUIRED` appears as its own stripped line. Claude may quote the protocol while working; substring matching causes false positives.

## Safety presets

Default to read-only unless Tomas explicitly requested edits or execution.

- **cheap_read** - `Read`, `--max-turns 2`, low effort. Default for quick repo/config/backlog inspections.
- **cheap_research** - `Read,WebSearch,WebFetch`, `--max-turns 3`, medium effort. Default for bounded web checks.
- **read_only** - `Read,WebSearch,WebFetch`, `--max-turns 5`, high effort. Research, inspection, strategy, summaries when cheap presets are too narrow.
- **code_review** - `Read,Bash(git *),Bash(python *),Bash(npm test*)`, `--max-turns 8`. Repo review, tests, diffs. No writes.
- **edit_with_approval** - `Read,Edit,Write,Bash(git *),Bash(python *),Bash(npm *)`, `--max-turns 15`. Only after scope is clear and Tomas requested implementation. Claude stops after changes + verification, does not commit unless asked.
- **long_tmux** - named tmux session for long interactive or multi-stage work needing monitoring or slash commands. Clean up when done.

## Command patterns

Print mode for one-shot work. Workers default to Sonnet (`claude-sonnet-5`); Opus only on explicit ask or clear need.

```bash
claude -p "$TASK_PACKET" --output-format json --model claude-sonnet-5 --max-turns 5 --effort high --allowedTools 'Read,WebSearch,WebFetch'
```

Code review:

```bash
claude -p "$TASK_PACKET" --output-format json --model claude-sonnet-5 --max-turns 8 --effort high --allowedTools 'Read,Bash(git *),Bash(python *),Bash(npm test*)'
```

Edits after approval:

```bash
claude -p "$TASK_PACKET" --output-format json --model claude-sonnet-5 --max-turns 15 --effort high --allowedTools 'Read,Edit,Write,Bash(git *),Bash(python *),Bash(npm *)'
```

Resume a prior session:

```bash
claude -p "$FOLLOWUP_PACKET" --resume "$SESSION_ID" --output-format json --max-turns 5 --effort high --allowedTools '<same or narrower preset>'
```

## Task packet template

```text
You are Claude Code acting as the heavy-lift worker for Hermes.
Hermes is the channel-facing orchestrator and will communicate with Tomas.

User goal:
<exact user goal>

Context from Hermes:
<minimal relevant context, file paths, constraints, prior messages - no Hermes commentary>

Verify target:
<expected output: passing test / file properties / diff / deliverable shape>
Verify command: <cmd>   (implementation tasks: run it, iterate until it passes,
report the final run's output; if no verifiable target exists, state confidence and gaps instead)

Use Claude capabilities:
- Load and apply all relevant installed skills, plugins, agents, and superpowers
  (planning, parallel agents, debugging, code review, TDD, execution, skill creation).
- Use project/global CLAUDE.md and installed plugin skills where relevant.

Clarification protocol:
If you need input from Tomas before proceeding, STOP and return exactly:
CLARIFICATION_REQUIRED
Question: <the question Hermes should ask Tomas>
Options: <optional choices, if helpful>
Why needed: <brief reason>
Do not continue until Hermes provides Tomas's answer.

Safety:
- Do not read secrets unless necessary and explicitly requested.
- Do not commit, push, delete, deploy, or schedule recurring jobs unless explicitly asked.
- For edits, stop after showing what changed and what was verified.

Output format:
- Executive summary
- Work performed / findings
- Verification: command run + result
- Risks / uncertainties
- Follow-up questions, if any
- What Hermes should tell Tomas
```

Keep the static protocol blocks (capabilities, clarification, safety, output format) byte-identical across delegations so prompt caching applies; dynamic context goes in the goal/context/verify slots.

## Session resumption after a usage reset

The Claude window resets at `block_end` in `~/.claude/usage-window.json` - never assume a fixed hour. If a session stalled only because usage ran out:

1. Resume the existing session (`--resume <session_id>`, or the existing tmux session for interactive work). Do not restart from scratch.
2. Tell Claude to continue from saved context: restate the last known goal, inspect partial work before acting.
3. Avoid duplicate side effects: check for already-created tasks, files, edits, jobs, comments before recreating anything.
4. Verify completion (readback/tests/diff) before telling Tomas it is done.

## Hermes post-processing responsibilities

After Claude returns:
1. Parse the JSON; capture `session_id`, `num_turns`, `subtype`, `total_cost_usd` in the thread ledger.
2. `subtype: error_max_turns` = INCOMPLETE handoff, not a completed task. Inspect git status/diff, finish or revert partial edits, then re-verify.
3. `CLARIFICATION_REQUIRED` on its own line = ask Tomas, then resume.
4. Run the verify command yourself for anything Claude claims done; inspect git diff and tests for edits.
5. Compress large output through the cheap tier before it enters Hermes context; keep channel replies concise, offer raw output only on request.

## Helper scripts (if present)

`~/.hermes/scripts/claude_delegate.py` (packets, presets, per-thread session ledger, dry-run, JSON parsing, clarification detection), `ollama_router.py`, and `claude_tmux_sweeper.py` are Mac-era helpers. **They are NOT currently installed on the agent box** (`~/.hermes/scripts/` does not exist there). On the box, build the command inline per the patterns above and keep the session ledger in working notes; the checklist and packet template above are the contract either way. If the helpers are restored, prefer them.

## Failure modes - do not repeat

- **Gate skipped.** Delegating without reading `usage-window.json`; the delegation and Tomas's interactive session share one 5h window.
- **Unbounded command.** Missing `--allowedTools` or `--max-turns`. Both are mandatory on every invocation.
- **No verify target.** "Do X" with no expected output or verify command; Claude one-shots blind and Hermes rubber-stamps it.
- **error_max_turns treated as done.** Partial edits reported as success. Inspect, finish or revert, verify, then report.
- **Clarification false positives.** Triggering the handoff on a quoted mention of the protocol instead of an own-line emission.
- **Guessing for Tomas.** Answering Claude's substantive question from Hermes's imagination instead of relaying it.
- **Session amnesia.** Fresh sessions instead of `--resume`; guessed session ids instead of ledger lookups.
- **Scratchpad leakage.** Forwarding Hermes's internal monologue inside the packet; it wastes tokens and confuses the worker.
- **`--dangerously-skip-permissions` from channel-triggered flows.** Never.
- **Unnamed or orphaned tmux sessions.** Name them, sweep them.
- **Blocked-command retry.** If a tool result says "Do NOT retry", do not rerun the same command; use a narrower verification or wait for Tomas's explicit go-ahead, then run the exact intended command once so the approval prompt can fire.
- **Cost fields taken literally.** `total_cost_usd` under Max-login auth is an estimate, not billing.
