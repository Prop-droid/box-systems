#!/usr/bin/env python3
"""dev-bot: Discord #dev channel -> Claude Code (Fable 5) sessions on the box.

Top-level message in #dev = new task -> creates a thread + fresh claude session.
Message inside a known thread = --resume of that thread's session.
State: sessions.json maps thread_id -> session_id.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

import discord

BASE = Path(__file__).resolve().parent
ENV = BASE / ".env"
SESSIONS_FILE = BASE / "sessions.json"

GUILD_ID = 1515766239228723410          # Agentic OS
DEV_CHANNEL_NAME = "dev"
ALLOWED_USERS = {385075348066271233}    # Tomas
CLAUDE_BIN = os.path.expanduser("~/.local/bin/claude")
MODEL = "claude-fable-5"
TIMEOUT_S = 30 * 60
CHUNK = 1900

GUARDRAILS = (
    "You are dev-bot, dispatched from the Agentic OS Discord #dev channel for "
    "development, system-fix and infra tasks across Tomas's fleet (see the "
    "fleet-control skill). Rules: (1) Destructive or hard-to-reverse operations "
    "(rm -rf, disabling/removing services or crons, resets, dropping data) require "
    "an explicit in-thread confirmation BEFORE running - state the exact command and "
    "wait for the next message. (2) Never push to work-account (tomas-ejam) repos. "
    "(3) Reply Hermes-style: lead with what changed + proof, short; this lands in "
    "Discord, so no giant walls of text. (4) If blocked on info only Tomas has, ask "
    "in one compact question."
)


def load_env():
    for line in ENV.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


def load_sessions() -> dict:
    try:
        return json.loads(SESSIONS_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_sessions(s: dict):
    tmp = SESSIONS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=1))
    tmp.replace(SESSIONS_FILE)


async def run_claude(prompt: str, resume: str | None) -> tuple[str, str | None]:
    """Returns (reply_text, session_id)."""
    cmd = [
        CLAUDE_BIN, "-p", prompt,
        "--model", MODEL,
        "--dangerously-skip-permissions",
        "--output-format", "json",
        "--append-system-prompt", GUARDRAILS,
    ]
    if resume:
        cmd += ["--resume", resume]
    env = dict(os.environ)
    env["PATH"] = os.path.expanduser("~/.local/bin") + ":" + env.get("PATH", "")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=os.path.expanduser("~"),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_S)
    except asyncio.TimeoutError:
        proc.kill()
        return ("⏱️ Task timed out after 30 min. The session is saved - reply here to continue it.", resume)
    if proc.returncode != 0:
        tail = (err or out or b"").decode(errors="replace")[-800:]
        return (f"❌ claude exited {proc.returncode}:\n```\n{tail}\n```", resume)
    try:
        data = json.loads(out.decode(errors="replace"))
        return (data.get("result") or "(empty result)", data.get("session_id") or resume)
    except json.JSONDecodeError:
        return (out.decode(errors="replace")[-1500:], resume)


class DevBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.sessions = load_sessions()
        self.locks: dict[int, asyncio.Lock] = {}
        self.dev_channel_id: int | None = None

    def resolve_dev_channel(self) -> int | None:
        if self.dev_channel_id is None:
            guild = self.get_guild(GUILD_ID)
            chan = discord.utils.get(guild.text_channels, name=DEV_CHANNEL_NAME) if guild else None
            if chan:
                self.dev_channel_id = chan.id
                print(f"dev-bot: watching #{chan.name} ({chan.id})", flush=True)
        return self.dev_channel_id

    async def on_ready(self):
        print(f"dev-bot ready as {self.user}; #dev found: {self.resolve_dev_channel() is not None}", flush=True)

    def lock_for(self, tid: int) -> asyncio.Lock:
        return self.locks.setdefault(tid, asyncio.Lock())

    async def send_chunked(self, dest, text: str):
        text = text.strip() or "(no output)"
        for i in range(0, len(text), CHUNK):
            await dest.send(text[i:i + CHUNK])

    async def handle_task(self, thread: discord.Thread, prompt: str, resume: str | None):
        async with self.lock_for(thread.id):
            async with thread.typing():
                reply, session_id = await run_claude(prompt, resume)
            if session_id:
                self.sessions[str(thread.id)] = session_id
                save_sessions(self.sessions)
            await self.send_chunked(thread, reply)

    async def on_message(self, msg: discord.Message):
        if msg.author.bot or msg.author.id not in ALLOWED_USERS:
            return
        if not msg.content.strip():
            return
        dev_id = self.resolve_dev_channel()
        if dev_id is None:
            return
        # Follow-up inside a thread under #dev
        if isinstance(msg.channel, discord.Thread) and msg.channel.parent_id == dev_id:
            resume = self.sessions.get(str(msg.channel.id))
            asyncio.create_task(self.handle_task(msg.channel, msg.content, resume))
            return
        # New task in #dev
        if msg.channel.id == dev_id:
            name = msg.content.strip().replace("\n", " ")[:80] or "dev task"
            thread = await msg.create_thread(name=name)
            asyncio.create_task(self.handle_task(thread, msg.content, None))


def main():
    load_env()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        sys.exit("DISCORD_TOKEN missing in .env")
    DevBot().run(token)


if __name__ == "__main__":
    main()
