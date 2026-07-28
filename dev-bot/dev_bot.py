#!/usr/bin/env python3
"""channel-agent: a Discord channel -> Claude Code sessions on the box.

Top-level message in the watched channel = new task -> creates a thread + fresh
claude session. Message inside a known thread = --resume of that thread's session.
State: sessions.json maps thread_id -> session_id.

Instances are configured via .env in BOT_DIR (default: script dir):
  DISCORD_TOKEN=...                      # required
  CHANNEL_NAME=dev                       # channel to watch
  CLAUDE_CWD=/home/tomas                 # cwd for claude sessions
  SYSTEM_PROMPT_FILES=/path/a:/path/b    # optional, concatenated; else default guardrails
  MODEL=claude-fable-5

Messages that @mention a bot are ignored here — those belong to the agentic-bots
persona runner (draft-and-approve), which answers DMs/@mentions. Plain channel
messages belong to this executor.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

import discord

BASE = Path(os.environ.get("BOT_DIR", Path(__file__).resolve().parent))
ENV = BASE / ".env"
SESSIONS_FILE = BASE / "sessions.json"

GUILD_ID = 1515766239228723410          # Agentic OS
ALLOWED_USERS = {385075348066271233}    # Tomas
CLAUDE_BIN = os.path.expanduser("~/.local/bin/claude")
TIMEOUT_S = 30 * 60
CHUNK = 1900

DEFAULT_GUARDRAILS = (
    "You are dispatched from a Discord channel in Tomas's Agentic OS server for "
    "development, system-fix and infra tasks across his fleet (see the "
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


def system_prompt() -> str:
    files = os.environ.get("SYSTEM_PROMPT_FILES", "")
    if not files:
        return DEFAULT_GUARDRAILS
    parts = []
    for p in files.split(":"):
        try:
            parts.append(Path(p).read_text().strip())
        except OSError as e:
            print(f"WARN: system prompt file {p}: {e}", flush=True)
    return "\n\n".join(parts) or DEFAULT_GUARDRAILS


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
        "--model", os.environ.get("MODEL", "claude-fable-5"),
        "--dangerously-skip-permissions",
        "--output-format", "json",
        "--append-system-prompt", system_prompt(),
    ]
    if resume:
        cmd += ["--resume", resume]
    env = dict(os.environ)
    env["PATH"] = os.path.expanduser("~/.local/bin") + ":" + env.get("PATH", "")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=os.path.expanduser(os.environ.get("CLAUDE_CWD", "~")),
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


class ChannelAgent(discord.Client):
    def __init__(self, channel_name: str):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.channel_name = channel_name
        self.sessions = load_sessions()
        self.locks: dict[int, asyncio.Lock] = {}
        self.channel_id: int | None = None

    def resolve_channel(self) -> int | None:
        if self.channel_id is None:
            guild = self.get_guild(GUILD_ID)
            chan = discord.utils.get(guild.text_channels, name=self.channel_name) if guild else None
            if chan:
                self.channel_id = chan.id
                print(f"channel-agent: watching #{chan.name} ({chan.id})", flush=True)
        return self.channel_id

    async def on_ready(self):
        print(f"channel-agent ready as {self.user}; #{self.channel_name} found: "
              f"{self.resolve_channel() is not None}", flush=True)

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
        if any(m.bot for m in msg.mentions):
            return  # @mentions belong to the agentic-bots persona runner
        chan_id = self.resolve_channel()
        if chan_id is None:
            return
        # Follow-up inside a thread under the watched channel
        if isinstance(msg.channel, discord.Thread) and msg.channel.parent_id == chan_id:
            resume = self.sessions.get(str(msg.channel.id))
            asyncio.create_task(self.handle_task(msg.channel, msg.content, resume))
            return
        # New task in the watched channel
        if msg.channel.id == chan_id:
            name = msg.content.strip().replace("\n", " ")[:80] or "task"
            thread = await msg.create_thread(name=name)
            asyncio.create_task(self.handle_task(thread, msg.content, None))


def main():
    load_env()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        sys.exit("DISCORD_TOKEN missing in .env")
    ChannelAgent(os.environ.get("CHANNEL_NAME", "dev")).run(token)


if __name__ == "__main__":
    main()
