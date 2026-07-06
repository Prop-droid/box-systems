---
name: hermes-routing-policy
description: Decide WHERE each incoming Hermes turn runs - direct in Hermes (GPT/Codex), delegated to Claude Code, or through the cheap model tier. Run on EVERY new user message, before drafting a reply or invoking tools. Includes the mandatory Claude usage-window gate (~/.claude/usage-window.json) that protects Tomas's 5h Claude subscription window before any delegation. Does NOT cover HOW to delegate (commands, packets, presets, clarification handoff - use delegate-to-claude) or how to size a heavy run (use claude-heavy-lifting).
version: 2.0.0
author: Hermes Agent + Tomas workflow
metadata:
  hermes:
    tags: [routing, orchestration, claude, gpt, cost, usage-window, whatsapp]
    related_skills: [delegate-to-claude, claude-heavy-lifting, claude-code, hermes-agent]
---

# Hermes Routing Policy

Hermes is a thin orchestrator for turns that arrive at Hermes (WhatsApp, Discord, CLI). Every turn picks ONE primary executor: Hermes-direct, Claude Code, or the cheap tier. System-wide, Claude Code remains Tomas's primary worker and orchestrator; this policy keeps Hermes lean, it does not make Hermes the brain.

This skill is WHEN to route. For HOW to delegate (commands, presets, packet template, clarification handoff, verify targets), see `delegate-to-claude`. For sizing heavy runs, see `claude-heavy-lifting`.

## Roles and billing reality

- **Hermes (gpt-5.5 via Codex, Gemini fallback)** - orchestrator, messenger, safety gate, final summarizer. Bills to OpenAI/Google. Hermes's own turns do NOT draw the Claude subscription cap.
- **Claude Code (`claude` CLI via Tomas's Max login)** - heavy-lift worker. Every delegation draws the SAME 5h Claude window Tomas's interactive sessions use. This is the shared scarce resource; the gate below exists to protect it.
- **Cheap tier** - Hermes's delegation model (Gemini 3.5 Flash on the box, `delegation:` in `~/.hermes/config.yaml`; Ollama only where actually installed - it is NOT installed on the agent box). Router, classifier, compressor. Keeps large blobs out of Hermes context without touching the Claude window.

## The usage-window gate (mandatory before any Claude delegation)

Before tier 2, read `~/.claude/usage-window.json` (written every 5 min by the usage-guard timer):

```json
{"pct":26,"tokens":25633105,"limit":96177496,"block_end":"2026-07-06T00:00:00.000Z","updated":"..."}
```

- **pct < 70** - delegate normally.
- **pct 70-89** - delegate, but prefer cheap presets (`cheap_read`/`cheap_research`); defer non-urgent batch or heavy work past `block_end`.
- **pct >= 90 during 08:00-23:00 Europe/Vilnius** - KILL new heavy delegations. Answer in Hermes, use the cheap tier, or queue until `block_end`. Tell Tomas in one line that Claude work is queued for the window reset.
- **`~/.claude/PAUSE_CLAUDE_BG` exists** - usage-guard has paused background Claude work. Do not add delegations unless Tomas explicitly asks for THIS task to run now.
- **`updated` older than ~15 min** - guard may be down; treat pct as unknown and cap any delegation at a cheap preset until confirmed.
- **Night (23:00-08:00)** - burning to 100% is allowed by design; the driver's own limit-retry handles it.

Never hardcode a reset hour. Reset times have drifted repeatedly (19:00, 00:30, midnight UTC); `block_end` in the JSON is the only truth. If the file is missing entirely, run one `cheap_read` probe at most and flag the guard as down.

## Tiered routing rules

Pick the first rule that matches.

### 1. Stay in Hermes (direct reply, no delegation)
- Short conversational turn, under ~500 tokens of user input, no files/URLs/code.
- Status checks: "did X run?", "what's the gateway state?", "ack".
- Messaging, scheduling, reminders, gateway/connection checks.
- Concise summary of a Claude result already returned this thread.
- The routing decision itself, packet preparation, parsing Claude JSON.

### 2. Delegate to Claude Code (after the usage-window gate passes)
Trigger if ANY apply:
- Payload over ~1.5k tokens of user-provided content.
- User pastes/attaches files, logs, transcripts, long quotes, or links Hermes would otherwise fetch.
- Task requires reading or editing a codebase, running tests, browser automation, scraping, or Drive/Obsidian workspace work.
- Task is plausibly more than 2 Hermes turns (deep research, planning, synthesis, refactor, code review).
- User says: "use Claude", "ask Claude", "pass to Claude", "deep research", "heavy lifting", "ultrathink", "full analysis", or asks to conserve GPT/Codex usage.
- Follow-up in an existing Claude thread (resume by `session_id`).

Hand substantial user content off RAW. Hermes pre-analyzing it burns GPT tokens on content Claude reads anyway.

### 3. Use the cheap tier for
- Intent classification before deciding tier 1 vs 2.
- Compressing long terminal/Claude/log output before it enters Hermes context.
- Cheap drafts and low-stakes classification.
- Stripping or sanity-checking blobs that would otherwise inflate Hermes context.

## Routing checklist - ordered, each step has a kill criterion

Run before dispatching any tier-2 turn. A failed step means fix it, not proceed with a caveat.

0. **Usage-window gate.** KILL: launching a heavy delegation at >= 90% daytime, with the PAUSE flag present, or with stale/missing guard data treated as green.
1. **Single executor.** KILL: a Hermes deep-analysis pass AND a Claude delegation running for the same goal. Cheap-tier routing/compression as a pre-step is fine; it is not a parallel executor.
2. **Raw handoff.** KILL: Hermes summarizing or re-reading a big paste before delegating it.
3. **Session reuse.** KILL: spawning a fresh Claude session when the thread already has a `session_id`. Always `--resume`.
4. **Verify target named.** KILL: an implementation delegation without an expected output and a verify command in the packet (see `delegate-to-claude`). Analysis tasks name the expected deliverable shape instead.
5. **Bounded run.** KILL: any `claude -p` without both `--max-turns` and `--allowedTools`.
6. **Clarification handoff intact.** Tier-2 packets carry the CLARIFICATION_REQUIRED protocol (verbatim block in `delegate-to-claude`). KILL: Hermes guessing an answer to a substantive Claude question instead of relaying it to Tomas and resuming with his answer.

If unsure between tier 1 and tier 2 and the gate is green, prefer tier 2: Claude can return fast and Hermes need only summarize.

## Claude cost discipline

The constraint is the shared 5h window (metered by usage-guard), not a weekly cap. To stretch it:

- **Session reuse.** One `session_id` per thread; `--resume` on follow-ups keeps the prompt cache warm.
- **Respect Tomas's terminal default.** Hermes may pick cheaper models for its own delegated workers, but never downgrades Tomas's interactive terminal default as an optimization.
- **Sonnet by default for workers.** Delegated workers default to Sonnet (`claude-sonnet-5`). Opus only when Tomas explicitly asks for max reasoning or the task clearly needs it.
- **Cache the static worker brief.** Keep the mandatory worker-protocol prompt identical across delegations; dynamic context goes AFTER the static brief.
- **Trim payloads.** Strip Hermes's own reasoning/scratchpad before forwarding.
- **No duplicate work.** Hermes does not re-analyze content it just sent to Claude; wait, then summarize.
- **Cap turns.** Default `cheap_read` (2 turns) for quick inspections, `cheap_research` (3 turns) for bounded web checks; fuller presets only when those are insufficient.
- **Compress before re-entry.** Large Claude output goes through the cheap tier before it lands in Hermes context.

## Edge cases and tie-breakers

- **Mixed turn (greeting + heavy task).** Acknowledge briefly in Hermes, then delegate. The greeting must not trigger a full GPT pass over the heavy content.
- **User pastes a link.** Tier 2. Hermes does not fetch URLs; Claude fetches with WebFetch/Firecrawl skills.
- **User pastes code.** Tier 2.
- **Long screenshot/transcript.** Tier 3 compress, then tier 1 if the gist is small, tier 2 if real analysis is needed.
- **"What did you just do?"** Tier 1, from Hermes's own log. Do not re-spawn Claude.
- **Gate is red but the task is urgent.** Ask Tomas: run now against the hot window, or queue for `block_end`. His call, one line.

## Failure modes - do not repeat

- **Cap-blind delegation.** Delegating heavy work without reading `usage-window.json`, then starving Tomas's interactive session. The gate is step 0, always.
- **Hardcoded reset times.** Citing "resets at 00:30" or any fixed hour. Read `block_end`.
- **Pre-digesting the payload.** Summarizing a 5k-token paste in Hermes before delegating; the content gets read twice and paid for twice.
- **Fresh session per turn.** Losing the prompt cache and the thread context; always resume.
- **Opus for routine delegations.** Sonnet unless explicitly justified.
- **Shadow work.** Running Hermes-side analysis "just in case" while Claude works the same prompt; doubles spend, diverges state.
- **Raw dump re-entry.** Pasting multi-page Claude output into Hermes context uncompressed.
- **"Always delegate" as policy.** That just moves the bottleneck from GPT onto Tomas's Claude window; tier 1 and tier 3 exist for a reason.

## Telemetry (recommended)

Record per turn in working notes or a thread ledger: `executor`, `reason` (which tier rule fired), `usage_pct_at_launch`, `payload_tokens_in`/`tokens_out` estimates, `claude.session_id`/`num_turns`/`total_cost_usd` when applicable, `clarification_required`. Enough to spot routing drift and retune thresholds.

## Quick decision flow

```
new user message
  |
  +- short + no files/links/code -------------------> Hermes-direct (tier 1)
  |
  +- big paste / files / links / code / multi-step -> usage-window gate
  |       |
  |       +- pct >= 90 daytime or PAUSE flag -> answer in Hermes / queue for block_end
  |       +- pct 70-89 -> cheap preset delegation
  |       +- green -> Claude (tier 2):
  |              strip scratchpad, resume session_id,
  |              Sonnet + --max-turns + --allowedTools,
  |              verify target in packet,
  |              wait -> verify -> summarize -> reply
  |
  +- mid-size blob needing only a gist -------------> cheap tier compress -> re-evaluate
```

See `delegate-to-claude` for the command and packet template; `claude-heavy-lifting` for sizing big runs.
