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
import subprocess
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


def thread_title(text: str, fallback: str) -> str:
    """2-4 word thread name via a cheap haiku call; falls back to truncated text."""
    try:
        p = subprocess.run(
            [CLAUDE_BIN, "-p", "--model", "claude-haiku-4-5-20251001"],
            input="Name this task in 2-4 plain words, like a short ticket title. "
                  f"Reply with the title only, no quotes or punctuation.\n\nTask:\n{text[:600]}",
            capture_output=True, text=True, timeout=25, cwd=str(Path.home()))
        t = " ".join((p.stdout or "").split()).strip("\"'.,:;")
        if 0 < len(t) <= 80:
            return t
    except Exception as e:
        print(f"[title] error: {e}", flush=True)
    return fallback


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


def tool_phrase(name: str, inp: dict) -> str:
    """Plain-English 'what is happening now' phrase for a tool call. Never raw commands."""
    if name == "Bash":
        d = (inp.get("description") or "").strip().rstrip(".")
        return f"{d}…" if d else "Running a command…"
    if name == "Read":
        f = os.path.basename(inp.get("file_path", ""))
        return f"Reading {f}…" if f else "Reading a file…"
    if name in ("Edit", "Write", "NotebookEdit"):
        f = os.path.basename(inp.get("file_path", ""))
        return f"Editing {f}…" if f else "Editing a file…"
    if name in ("Grep", "Glob"):
        return "Searching the code…"
    if name in ("Task", "Agent"):
        d = (inp.get("description") or "").strip()
        return f"Delegating: {d}…" if d else "Delegating a subtask…"
    if name == "Skill":
        s = inp.get("skill", "")
        return f"Using the {s} skill…" if s else "Loading a skill…"
    if name == "WebSearch":
        q = snippet(inp.get("query", ""), 50)
        return f"Searching the web: {q}…" if q else "Searching the web…"
    if name == "WebFetch":
        return "Reading a webpage…"
    if name.startswith("mcp__"):
        return f"Using {name.split('__')[-1]}…"
    return f"Using {name}…"


class StatusBoard:
    """One Discord message per task, edited in place: current activity + checklist + counters."""
    MIN_EDIT_GAP = 2.0  # seconds between edits (Discord rate limits)
    MAX_TODOS = 8

    MARKS = {"completed": "☑", "in_progress": "▸", "pending": "◻"}

    def __init__(self, thread: discord.Thread):
        self.thread = thread
        self.msg: discord.Message | None = None
        self.current = "Starting…"
        self.todos: list[dict] = []
        self.steps = 0
        self.started = time.monotonic()
        self._last_edit = 0.0
        self._pending: asyncio.Task | None = None
        self._done = False

    def _counter(self) -> str:
        return f"{self.steps} step" + ("s" if self.steps != 1 else "")

    def _elapsed(self) -> str:
        mins, secs = divmod(int(time.monotonic() - self.started), 60)
        return f"{mins}m {secs:02d}s" if mins else f"{secs}s"

    def _render(self, header: str) -> str:
        lines = [header]
        for td in self.todos[:self.MAX_TODOS]:
            mark = self.MARKS.get(td.get("status"), "◻")
            lines.append(f"{mark} {snippet(td.get('content', ''), 60)}")
        if len(self.todos) > self.MAX_TODOS:
            lines.append(f"… +{len(self.todos) - self.MAX_TODOS} more")
        if not self._done:
            lines.append(f"-# {self._counter()} · {self._elapsed()}")
        return "\n".join(lines)[:1990]

    async def _push(self, header: str | None = None):
        header = header or f"⏳ **{self.current}**"
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
        await self._push()

    async def on_block(self, block: dict):
        t = block.get("type")
        if t == "text":
            s = snippet(block.get("text", ""), 100)
            if not s:
                return
            self.current = s
        elif t == "tool_use":
            self.steps += 1
            name = block.get("name", "?")
            inp = block.get("input") or {}
            if name == "TodoWrite":
                self.todos = inp.get("todos") or []
                active = next((td for td in self.todos if td.get("status") == "in_progress"), None)
                if active:
                    self.current = snippet(active.get("activeForm", ""), 80) + "…"
            else:
                self.current = tool_phrase(name, inp)
        else:
            return  # thinking etc. — narration text covers it
        gap = time.monotonic() - self._last_edit
        if gap >= self.MIN_EDIT_GAP:
            await self._push()
        elif self._pending is None or self._pending.done():
            self._pending = asyncio.create_task(self._delayed_push(self.MIN_EDIT_GAP - gap))

    async def finish(self, header_icon: str):
        if self._pending and not self._pending.done():
            self._pending.cancel()
        self._done = True
        word = {"✅": "Done", "❌": "Failed", "⏱️": "Timed out"}.get(header_icon, "Done")
        await self._push(f"{header_icon} {word} · {self._counter()} · {self._elapsed()}")


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


async def run_claude(prompt: str, resume: str | None, on_block=None,
                     cwd: str | None = None, model: str | None = None,
                     sys_prompt: str | None = None) -> tuple[str, str | None]:
    """Streams claude's work via on_block(content_block). Returns (reply_text, session_id).
    cwd/model/sys_prompt override the instance .env config (used by general_bot)."""
    cmd = [
        CLAUDE_BIN, "-p", prompt,
        "--model", model or os.environ.get("MODEL", "claude-fable-5"),
        "--dangerously-skip-permissions",
        "--output-format", "stream-json",
        "--verbose",
        "--append-system-prompt", sys_prompt or system_prompt(),
    ]
    if resume:
        cmd += ["--resume", resume]
    env = dict(os.environ)
    env["PATH"] = os.path.expanduser("~/.local/bin") + ":" + env.get("PATH", "")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=os.path.expanduser(cwd or os.environ.get("CLAUDE_CWD", "~")),
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
        self.queues: dict[int, list[str]] = {}
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

    def queue_for(self, tid: int) -> list[str]:
        return self.queues.setdefault(tid, [])

    async def enqueue(self, thread: discord.Thread, prompt: str, msg: discord.Message | None = None):
        """Terminal-style: messages sent while a task runs are queued, never interrupt it.
        They're delivered (batched) to the same session as soon as the current turn ends."""
        self.queue_for(thread.id).append(prompt)
        if self.lock_for(thread.id).locked():
            if msg:
                try:
                    await msg.add_reaction("📨")
                except discord.HTTPException:
                    pass
            return
        asyncio.create_task(self.drain(thread))

    async def drain(self, thread: discord.Thread):
        async with self.lock_for(thread.id):
            q = self.queue_for(thread.id)
            while q:
                prompt = "\n\n".join(q)
                q.clear()
                resume = self.sessions.get(str(thread.id))  # resolved NOW, not at message time
                board = StatusBoard(thread)
                async with thread.typing():
                    reply, session_id = await run_claude(prompt, resume, on_block=board.on_block)
                await board.finish("⏱️" if reply.startswith("⏱️") else "❌" if reply.startswith("❌") else "✅")
                if session_id:
                    self.sessions[str(thread.id)] = session_id
                    save_sessions(self.sessions)
                await self.send_chunked(thread, reply)
        if self.queue_for(thread.id):  # message raced in between final check and lock release
            asyncio.create_task(self.drain(thread))

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
            prompt = with_attachments(msg.content, await save_attachments(msg))
            await self.enqueue(msg.channel, prompt, msg)
            return
        # New task in the watched channel
        if msg.channel.id == chan_id:
            files = await save_attachments(msg)
            fallback = (msg.content.strip().replace("\n", " ")[:80]
                        or (msg.attachments[0].filename[:80] if msg.attachments else "task"))
            name = await asyncio.to_thread(thread_title, msg.content or fallback, fallback)
            thread = await msg.create_thread(name=name)
            await self.enqueue(thread, with_attachments(msg.content, files))


def main():
    load_env()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        sys.exit("DISCORD_TOKEN missing in .env")
    ChannelAgent(os.environ.get("CHANNEL_NAME", "dev")).run(token)


if __name__ == "__main__":
    main()
