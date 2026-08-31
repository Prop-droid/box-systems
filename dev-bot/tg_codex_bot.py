#!/usr/bin/env python3
"""tg-qa-bot: Telegram transport for the Codex-engined QA agent.

telegram_bot's drain() resolves dev_bot.run_claude at call time; swapping in
codex_bot.run_codex before the loop starts gives the QA agent (Codex CLI)
the same Telegram surface as the Claude bots. BOT_DIR selects the instance
(~/systems/tg-qa-bot — memory/ is a symlink to the Discord qa-bot instance,
so the agent's self-edited memory carries across transports).
"""
import codex_bot
import dev_bot
import telegram_bot

dev_bot.run_claude = codex_bot.run_codex

if __name__ == "__main__":
    telegram_bot.main()
