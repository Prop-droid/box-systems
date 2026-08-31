# Discord → Telegram migration (decided 2026-08-06, deep-dive 2026-08-31)

Tomas's call: migrate the Agentic OS off Discord onto Telegram. The beachhead
(tg-dev-bot, live since 08-07) proved the transport; this spec covers the full
estate. Discord stays running in parallel until Phase 4 — nothing is disabled
without an explicit go.

## Why Telegram wins
4096-char messages (vs 2000), native documents for long replies, better mobile
UX, voice notes as attachments, and Tomas lives in Telegram. Costs (below) are
all solvable or acceptable.

## Target architecture
- **One supergroup per agent**, Topics ON, topic-per-task (mirrors
  channel-per-agent on Discord): Agent OS (= Developer, exists) + EA OS +
  Creative OS + Coach OS + QA OS. DM with each bot = quick rolling session.
- Same engine reuse as Discord: `telegram_bot.py` imports `dev_bot`,
  `BOT_DIR` selects the instance. QA runs `tg_codex_bot.py`
  (monkeypatches `dev_bot.run_claude = codex_bot.run_codex`).
- **Auto-adopt**: with `ALLOWED_USER_IDS` preset and `CHAT_ID` unset, each bot
  adopts the first group Tomas messages it from — box-side setup is zero-touch.

## Platform gaps and how we close them
| Discord capability | Telegram reality | Resolution |
|---|---|---|
| History API (`discord_read.py`, context injection) | Bot API has NO history fetch | **Archive-at-source** (shipped 08-31): every instance logs inbound/outbound/topics to `dev-bot/tg_archive/<chat>.jsonl`; `telegram_read.py` = recall CLI; fresh sessions get archive context injected. History only accrues from 08-31 — cannot backfill. |
| Inter-agent @mention dispatch (`fleet_bots.json`) | Bots cannot see other bots' messages | Future: local dispatch bus on the box (host process parses its agent's reply for a handoff marker, drops a task file into the target instance's queue; each bot posts its own result to the shared topic). Not ported in v1 — executors are the daily surface. |
| #general haiku router + war-room personas (`agent_bots.py`, `general_bot.py`) | no multi-client channel model | **Retire, don't port.** The tool-less persona layer is a Discord-era artifact; executors + DMs cover the use. |
| ops-log webhook (`lib/discord-notify.sh`, 13+ callers) | no webhooks | `lib/tg-notify.sh` (shipped 08-31, signature-compatible) → 🔔 Ops Log topic (id 15) in Agent OS group. Cutover = swap the helper's callers' path, or symlink. |
| Hermes Discord (53 slash commands, voice_fx, backfill) | Hermes has first-class Telegram support built in | Set `TELEGRAM_BOT_TOKEN` in `~/.hermes/.env` (config.yaml `platforms.telegram` + `telegram:` block already exist), restart gateway. Slash commands re-register via BotFather `/setcommands` — fewer, simpler. |
| Coach DMs (`coach_notify.py`/`briefing.py` via QA_TOKEN) | simpler on Telegram | `telegram_dm()`: one `sendMessage` to Tomas's user id (6500354911) — no open-DM-channel step. Requires Tomas to have DM'd the coach bot once. |

## Phases

**Phase 1 — box staging (DONE 2026-08-31)**
- Instance dirs `tg-{ea,creative,coach,qa}-bot/` (.env templates: cwd/model/
  prompt-heads copied from the Discord instances; token empty). qa memory/ is a
  symlink to qa-bot/memory (agent identity carries across transports).
- Units `systemd/tg-{ea,creative,coach,qa}-bot.service` deployed **disabled**.
- `telegram_bot.py`: message archive + outbound archive + topic-name log +
  fresh-session context injection + guardrail rule 5 (telegram_read).
- `telegram_read.py` recall CLI; `lib/tg-notify.sh` + Ops Log topic (id 15,
  cached in `lib/.tg-ops-topic`); test alert delivered.

**Phase 2 — Tomas (~15 min, the only human-gated step)**
1. @BotFather → `/newbot` ×4: Exec Assistant, Creative Lead, Štuikys, QA
   Critique (usernames e.g. @agentbox_ea_bot, @agentbox_creative_bot,
   @agentbox_coach_bot, @agentbox_qa_bot).
2. Paste the 4 tokens to any box agent (Telegram DM to @agentbox_dev_bot is
   fine) → it fills `~/systems/tg-*-bot/.env` and `systemctl --user enable
   --now` the units.
3. Create 4 groups (EA OS, Creative OS, Coach OS, QA OS): enable Topics, add
   the matching bot, promote to Admin with Manage Topics, send "hi" → adopted.
4. Optional now / later: one more bot for Hermes → `TELEGRAM_BOT_TOKEN` in
   `~/.hermes/.env`, restart hermes-gateway.

**Phase 3 — box cutover work (after tokens; no Discord disabled yet)**
- Prompt heads: replace `discord_read.py` references with `telegram_read.py`
  in the 4 `system_prompt_head.txt` files (+ wire them into tg .envs — done in
  templates already); neutralize "lands in Discord" phrasing.
- Alert surfaces: point `discord-notify.sh` callers at `tg-notify.sh` (one
  helper swap covers ~13 timers); port the 2 bypass scripts
  (`viral-trend-tracker/run_digest.sh` → Creative OS group,
  `launch-details-scan/scan.py` → EA OS group).
- Coach: `telegram_dm()` in coach_notify.py/briefing.py (dedupe the copy).
- `creative-feedback/mine_verdicts.py`: read from telegram_read instead of
  discord_read (keep Discord read during parallel-run for old history).
- Hermes: token + `/setcommands`; populate `channel_directory.json` telegram.

**Phase 4 — decommission (gated on Tomas's explicit go, per destructive-ops rule)**
- Stop/disable: dev/ea/creative/coach/qa/general-bot.service, agentic-bots.service.
- `box-watchdog.sh`: swap `agentic-bots` assertion for tg units; move its
  notify to tg-notify permanently.
- Keep `discord_read.py` + tokens for archival reads; Discord server itself
  can idle indefinitely.

## Rollback
Everything is additive until Phase 4. Discord bots untouched; tg units can be
stopped/disabled at any time; `tg-notify.sh` failing is fail-open (exit 0).
