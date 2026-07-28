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
import re
import sys
import time
from pathlib import Path

import discord

BASE = Path(os.environ.get("BOT_DIR", Path(__file__).resolve().parent))
ENV = BASE / ".env"
SESSIONS_FILE = BASE / "sessions.json"

GUILD_ID = 1515766239228723410          # Agentic OS
ALLOWED_USERS = {385075348066271233}    # Tomas
DROPS_DIR = Path.home() / "Downloads" / "discord-drops"
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


def snippet(text: str, n: int = 80) -> str:
    line = " ".join(text.strip().split())
    return line[:n] + ("…" if len(line) > n else "")


def describe_block(block: dict) -> str | None:
    """One activity-log line for a stream content block, or None to skip."""
    t = block.get("type")
    if t == "thinking":
        s = snippet(block.get("thinking", ""))
        return f"💭 {s}" if s else None
    if t == "text":
        s = snippet(block.get("text", ""))
        return f"💬 {s}" if s else None
    if t != "tool_use":
        return None
    name = block.get("name", "?")
    inp = block.get("input") or {}
    if name == "Bash":
        arg = inp.get("description") or inp.get("command", "")
    elif name in ("Read", "Edit", "Write", "NotebookEdit"):
        arg = os.path.basename(inp.get("file_path", ""))
    elif name in ("Grep", "Glob"):
        arg = inp.get("pattern", "")
    elif name in ("Task", "Agent"):
        arg = inp.get("description", "")
    elif name == "Skill":
        arg = inp.get("skill", "")
    elif name == "WebFetch":
        arg = inp.get("url", "")
    elif name == "WebSearch":
        arg = inp.get("query", "")
    elif name == "TodoWrite":
        todos = inp.get("todos") or []
        active = next((t2 for t2 in todos if t2.get("status") == "in_progress"), None)
        arg = active.get("activeForm", "") if active else f"{len(todos)} items"
    else:
        arg = ""
    return f"🔧 {name}" + (f": {snippet(arg, 70)}" if arg else "")


class StatusBoard:
    """One Discord message per task, edited in place with a rolling activity log."""
    KEEP = 12          # log lines shown
    MIN_EDIT_GAP = 2.0  # seconds between edits (Discord rate limits)

    def __init__(self, thread: discord.Thread):
        self.thread = thread
        self.msg: discord.Message | None = None
        self.lines: list[str] = []
        self.steps = 0
        self.started = time.monotonic()
        self._last_edit = 0.0
        self._pending: asyncio.Task | None = None

    def _render(self, header: str) -> str:
        body = "\n".join(self.lines[-self.KEEP:])
        return f"{header}\n{body}"[:1990] if body else header

    async def _push(self, header: str):
        try:
            if self.msg is None:
                self.msg = await self.thread.send(self._render(header))
            else:
                await self.msg.edit(content=self._render(header))
            self._last_edit = time.monotonic()
        except discord.HTTPException as e:
            print(f"WARN: status edit failed: {e}", flush=True)

    async def _delayed_push(self, delay: float):
        await asyncio.sleep(delay)
        await self._push("⏳ **Working…**")

    async def on_block(self, block: dict):
        line = describe_block(block)
        if not line or (self.lines and self.lines[-1] == line):
            return
        if block.get("type") == "tool_use":
            self.steps += 1
        self.lines.append(line)
        gap = time.monotonic() - self._last_edit
        if gap >= self.MIN_EDIT_GAP:
            await self._push("⏳ **Working…**")
        elif self._pending is None or self._pending.done():
            self._pending = asyncio.create_task(self._delayed_push(self.MIN_EDIT_GAP - gap))

    async def finish(self, header_icon: str):
        if self._pending and not self._pending.done():
            self._pending.cancel()
        mins, secs = divmod(int(time.monotonic() - self.started), 60)
        await self._push(f"{header_icon} {self.steps} tool calls · {mins}m {secs:02d}s")


async def save_attachments(msg: discord.Message) -> list[str]:
    """Download message attachments to DROPS_DIR; returns the saved paths."""
    paths: list[str] = []
    if not msg.attachments:
        return paths
    DROPS_DIR.mkdir(parents=True, exist_ok=True)
    for att in msg.attachments:
        name = re.sub(r"[^\w.\- ]", "_", att.filename).strip() or "file"
        path = DROPS_DIR / f"{msg.id}-{name}"
        try:
            await att.save(path)
            paths.append(str(path))
        except (discord.HTTPException, OSError) as e:
            print(f"WARN: attachment save failed ({att.filename}): {e}", flush=True)
    return paths


def with_attachments(content: str, paths: list[str]) -> str:
    if not paths:
        return content
    listing = "\n".join(paths)
    return (f"{content}\n\n[Attachments from this Discord message, saved on the box:\n"
            f"{listing}\nUse these files as part of the task.]")


async def run_claude(prompt: str, resume: str | None, on_block=None) -> tuple[str, str | None]:
    """Streams claude's work via on_block(content_block). Returns (reply_text, session_id)."""
    cmd = [
        CLAUDE_BIN, "-p", prompt,
        "--model", os.environ.get("MODEL", "claude-fable-5"),
        "--dangerously-skip-permissions",
        "--output-format", "stream-json",
        "--verbose",
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
        limit=10 * 1024 * 1024,
    )
    stderr_task = asyncio.create_task(proc.stderr.read())
    loop = asyncio.get_running_loop()
    deadline = loop.time() + TIMEOUT_S
    result_text: str | None = None
    session_id = resume
    try:
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise asyncio.TimeoutError
            line = await asyncio.wait_for(proc.stdout.readline(), remaining)
            if not line:
                break
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = ev.get("type")
            if t == "system" and ev.get("subtype") == "init":
                session_id = ev.get("session_id") or session_id
            elif t == "assistant" and on_block:
                for block in (ev.get("message") or {}).get("content") or []:
                    await on_block(block)
            elif t == "result":
                result_text = ev.get("result")
                session_id = ev.get("session_id") or session_id
    except asyncio.TimeoutError:
        proc.kill()
        stderr_task.cancel()
        return ("⏱️ Task timed out after 30 min. The session is saved - reply here to continue it.", session_id)
    rc = await proc.wait()
    err = await stderr_task
    if result_text is None:
        tail = (err or b"").decode(errors="replace")[-800:]
        return (f"❌ claude exited {rc}:\n```\n{tail or '(no output)'}\n```", session_id)
    return (result_text or "(empty result)", session_id)


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
            board = StatusBoard(thread)
            async with thread.typing():
                reply, session_id = await run_claude(prompt, resume, on_block=board.on_block)
            await board.finish("⏱️" if reply.startswith("⏱️") else "❌" if reply.startswith("❌") else "✅")
            if session_id:
                self.sessions[str(thread.id)] = session_id
                save_sessions(self.sessions)
            await self.send_chunked(thread, reply)

    async def on_message(self, msg: discord.Message):
        if msg.author.bot or msg.author.id not in ALLOWED_USERS:
            return
        if not msg.content.strip() and not msg.attachments:
            return
        if any(m.bot for m in msg.mentions):
            return  # @mentions belong to the agentic-bots persona runner
        chan_id = self.resolve_channel()
        if chan_id is None:
            return
        # Follow-up inside a thread under the watched channel
        if isinstance(msg.channel, discord.Thread) and msg.channel.parent_id == chan_id:
            resume = self.sessions.get(str(msg.channel.id))
            prompt = with_attachments(msg.content, await save_attachments(msg))
            asyncio.create_task(self.handle_task(msg.channel, prompt, resume))
            return
        # New task in the watched channel
        if msg.channel.id == chan_id:
            files = await save_attachments(msg)
            name = (msg.content.strip().replace("\n", " ")[:80]
                    or (msg.attachments[0].filename[:80] if msg.attachments else "task"))
            thread = await msg.create_thread(name=name)
            asyncio.create_task(self.handle_task(thread, with_attachments(msg.content, files), None))


def main():
    load_env()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        sys.exit("DISCORD_TOKEN missing in .env")
    ChannelAgent(os.environ.get("CHANNEL_NAME", "dev")).run(token)


if __name__ == "__main__":
    main()
