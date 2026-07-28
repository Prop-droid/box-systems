# dev-bot — Discord #dev channel → Claude Code (Fable 5) on the agent box

**Date:** 2026-07-28 · **Status:** approved in chat (Tomas), built same day

## Purpose
Dev/system-fix tasks (the "tablet night mode" kind) dispatched from Discord instead of
loading the main interactive session. Each task gets a fresh Claude Code session with
full fleet access; follow-ups continue in a Discord thread.

## Decisions (from brainstorm)
- **Identity:** existing **Developer** bot in the Agentic OS server (guild 1515766239228723410) — own token, zero coupling to Hermes. Hermes stays untouched as backup.
- **Channel:** `#dev`. Top-level message = new task → bot creates a thread → replies there.
- **Sessions:** thread = session. New top-level message spawns `claude -p` (fresh session, captures session id); replies inside a thread `--resume` that session. Map persisted in `sessions.json`.
- **Model:** `claude-fable-5`. **Permissions:** `--dangerously-skip-permissions` + appended system-prompt guardrails: destructive/irreversible ops confirmed in-thread first, no work-repo pushes, Hermes-style short replies (what changed + proof).
- **Fleet access:** runs on the box as user `tomas`, so SSH/adb/Fully REST reach per fleet-control skill is inherited.

## Components
- `~/systems/dev-bot/dev_bot.py` — single-file discord.py service. Filters: guild = Agentic OS, channel = #dev (+ its threads), author = Tomas (385075348066271233). Async subprocess, per-thread lock (follow-ups queue), 30-min timeout, 1900-char reply chunking, typing indicator.
- `~/systems/dev-bot/.env` — `DISCORD_TOKEN` (chmod 600, NOT in git).
- `~/systems/dev-bot/sessions.json` — thread_id → {session_id, cwd} map.
- `~/systems/systemd/dev-bot.service` — user unit, Restart=always.

## Error handling
- Claude subprocess non-zero / timeout → error posted into the thread, session map kept.
- Unknown thread (no map entry) → treated as new session inside that thread.
- Gateway 4014 (Message Content intent off) → logged clearly; fix = portal toggle (URL handoff).

## Verification target
Tomas posts "what box are you running on?" in #dev → thread appears, Fable 5 answer
lands in it; a follow-up in the thread shows session continuity (remembers the task).
