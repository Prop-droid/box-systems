#!/usr/bin/env python3
"""general-bot: #general -> haiku router -> the right channel-agent picks it up.

One process, four Discord clients (Developer / Štuikys / Exec Assistant /
Creative Lead — same tokens as their per-channel executor services). Top-level
message in #general: a cheap haiku call picks the best-fit profile, then THAT
bot creates the thread and runs the task with its own cwd + system prompt.
Thread replies resume the session under the owning profile.
State: general_sessions.json maps thread_id -> {profile, session, sessions{key: id}}.
Mention dispatch (2026-07-29): @mentioning a profile bot in #general (channel or
thread) dispatches THAT profile directly, bypassing the router; several mentioned
profiles join the same thread as a panel, each with its own session ("sessions"
map; "profile"/"session" stay the plain-follow-up owner). Mentions of bots that
are not profiles here (e.g. Copywriter) still belong to the persona runner.
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

import discord

import codex_bot
import dev_bot
from dev_bot import (ALLOWED_USERS, CLAUDE_BIN, DEFAULT_GUARDRAILS, GUILD_ID,
                     TRUSTED_BOT_IDS, StatusBoard, run_claude, save_attachments,
                     with_attachments)

HERE = Path(__file__).resolve().parent
SESSIONS_FILE = HERE / "general_sessions.json"
CHANNEL_NAME = "general"
ROUTER_KEY = "dev"  # this profile's client classifies + owns unmapped threads

PROFILES = {
    "dev": {
        "dir": HERE,
        "route": "development, debugging, code, servers/services, crons, systemd, infra, fleet devices, files on the box",
    },
    "coach": {
        "dir": Path.home() / "systems/coach-bot",
        "route": "health, training, running, workouts, Garmin data, recovery, sleep, nutrition coaching",
    },
    "ea": {
        "dir": Path.home() / "systems/ea-bot",
        "route": "ClickUp tasks/backlog, calendars, scheduling, email, reminders, admin/organisation",
    },
    "creative": {
        "dir": Path.home() / "systems/creative-bot",
        "route": "marketing, ads, creative strategy, briefs, scripts/copy, brand questions, research, competitor/web lookups",
    },
    "qa": {
        "dir": Path.home() / "systems/qa-bot",
        "route": "QA review, critiquing/verifying another agent's work or plan, spec and naming compliance checks, test plans",
        "engine": "codex",
    },
}


def read_env(path: Path) -> dict:
    conf = {}
    for line in (path / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            conf[k] = v
    return conf


def load_profiles():
    for key, p in PROFILES.items():
        conf = read_env(p["dir"])
        p["token"] = conf["DISCORD_TOKEN"]
        p["cwd"] = conf.get("CLAUDE_CWD", str(Path.home()))
        p["model"] = conf.get("MODEL")
        parts = []
        for f in conf.get("SYSTEM_PROMPT_FILES", "").split(":"):
            if f:
                try:
                    parts.append(Path(f).read_text().strip())
                except OSError as e:
                    print(f"WARN: {key} prompt file {f}: {e}", flush=True)
        p["sys"] = "\n\n".join(parts) or DEFAULT_GUARDRAILS


def route(message: str) -> str:
    """Pick the profile key for a message. Cheap haiku call; falls back to dev."""
    menu = "\n".join(f"- {k}: {p['route']}" for k, p in PROFILES.items())
    prompt = (
        "Route Tomas's message to exactly ONE executor agent on his team.\n"
        f"Agents:\n{menu}\n\n"
        f"Message:\n{message}\n\n"
        f"Reply with ONLY the agent key ({', '.join(PROFILES)}). No other words."
    )
    try:
        p = subprocess.run([CLAUDE_BIN, "-p", "--model", "claude-haiku-4-5-20251001"],
                           input=prompt, capture_output=True, text=True, timeout=60,
                           cwd=str(Path.home()))
        out = (p.stdout or "").strip().lower()
        for k in sorted(PROFILES, key=len, reverse=True):  # 'ea' is inside 'creative'
            if k in out:
                return k
    except Exception as e:
        print(f"[router] error: {e}", flush=True)
    return ROUTER_KEY


class Shared:
    def __init__(self):
        self.clients: dict[str, discord.Client] = {}
        self.sessions = self._load()
        self.locks: dict[int, asyncio.Lock] = {}
        self.channel_id: int | None = None
        self.bot_dispatches: dict[int, list[float]] = {}

    def _load(self) -> dict:
        try:
            return json.loads(SESSIONS_FILE.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save(self):
        tmp = SESSIONS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.sessions, indent=1))
        tmp.replace(SESSIONS_FILE)

    def lock_for(self, tid: int) -> asyncio.Lock:
        return self.locks.setdefault(tid, asyncio.Lock())

    BOT_DISPATCH_MAX, BOT_DISPATCH_WINDOW = 5, 600  # per-channel inter-agent loop breaker

    def bot_dispatch_ok(self, cid: int) -> bool:
        import time
        now = time.monotonic()
        hist = self.bot_dispatches.setdefault(cid, [])
        hist[:] = [t for t in hist if now - t < self.BOT_DISPATCH_WINDOW]
        if len(hist) >= self.BOT_DISPATCH_MAX:
            print(f"WARN: inter-agent dispatch cap hit in {cid}", flush=True)
            return False
        hist.append(now)
        return True


async def handle_task(shared: Shared, key: str, thread: discord.Thread,
                      prompt: str, resume: str | None):
    p = PROFILES[key]
    async with shared.lock_for(thread.id):
        try:
            if resume is None:
                # profile joining an existing conversation — hand it the thread so far
                ctx = await dev_bot.thread_context(thread)
                if ctx:
                    prompt = (f"[Discord thread context so far, oldest first]\n{ctx}\n\n"
                              f"[Latest request addressed to you]\n{prompt}")
            runner = codex_bot.run_codex if p.get("engine") == "codex" else run_claude
            if (resume and runner is run_claude
                    and dev_bot.session_context_tokens(resume, cwd=p["cwd"]) > dev_bot.COMPACT_AT):
                # compaction fires the PreCompact memory-flush hook, so nothing is lost
                try:
                    note = await thread.send(
                        "🗜️ Session context near the 529 wedge zone — saving durable "
                        "knowledge to memory, then compacting (~2-4 min)…")
                    ok = await dev_bot.compact_session(resume, cwd=p["cwd"])
                    await note.edit(content="🗜️ Memory saved, session compacted." if ok else
                                    "🗜️ Compaction failed — continuing on the full context.")
                except discord.HTTPException:
                    pass
            board = StatusBoard(thread)
            async with thread.typing():
                reply, session_id = await runner(prompt, resume, on_block=board.on_block,
                                                 cwd=p["cwd"], model=p["model"],
                                                 sys_prompt=p["sys"])
            await board.finish("⏱️" if reply.startswith("⏱️") else "❌" if reply.startswith("❌") else "✅")
            if session_id:
                entry = shared.sessions.get(str(thread.id)) or {"profile": key}
                entry.setdefault("sessions", {})[key] = session_id
                if entry.get("profile", key) == key:
                    entry["profile"], entry["session"] = key, session_id
                shared.sessions[str(thread.id)] = entry
                shared.save()
            text = reply.strip() or "(no output)"
            for i in range(0, len(text), 1900):
                await thread.send(text[i:i + 1900])
        except Exception as e:
            # bare create_task — an uncaught exception here dies silently otherwise
            print(f"ERROR: handle_task[{key}]({thread.id}): {e!r}", flush=True)
            try:
                await thread.send(f"❌ Task crashed: `{e!r}`"[:1980] + "\nReply here to retry.")
            except Exception:
                pass


class GeneralAgent(discord.Client):
    def __init__(self, key: str, shared: Shared):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.key = key
        self.shared = shared

    def resolve_channel(self) -> int | None:
        if self.shared.channel_id is None:
            guild = self.get_guild(GUILD_ID)
            chan = discord.utils.get(guild.text_channels, name=CHANNEL_NAME) if guild else None
            if chan:
                self.shared.channel_id = chan.id
                print(f"general-bot: watching #{chan.name} ({chan.id})", flush=True)
        return self.shared.channel_id

    async def on_ready(self):
        print(f"general-bot [{self.key}] online as {self.user}", flush=True)
        self.resolve_channel()

    async def dispatch_new(self, msg: discord.Message, key: str | None = None):
        files = await save_attachments(msg)
        if key is None:
            key = await asyncio.to_thread(route, msg.content or (files and files[0]) or "task")
        client = self.shared.clients[key]
        chan = client.get_channel(msg.channel.id)
        m = await chan.fetch_message(msg.id)
        content = self.strip_mention(m, client.user,
                                     {r.id for r in getattr(chan.guild.me, "roles", [])})
        fallback = (content.strip().replace("\n", " ")[:80]
                    or (msg.attachments[0].filename[:80] if msg.attachments else "task"))
        name = await asyncio.to_thread(dev_bot.thread_title, content or fallback, fallback)
        try:
            thread = await m.create_thread(name=name)
        except discord.HTTPException:
            # another mentioned profile created it first (thread id == message id)
            thread = chan.get_thread(msg.id) or await client.fetch_channel(msg.id)
        await handle_task(self.shared, key, thread, with_attachments(content, files), None)

    @staticmethod
    def strip_mention(msg: discord.Message, user, role_ids=frozenset()) -> str:
        content = msg.content.replace(f"<@{user.id}>", "").replace(f"<@!{user.id}>", "")
        for r in msg.role_mentions:
            if r.managed and r.id in role_ids:
                content = content.replace(f"<@&{r.id}>", "")
        content = content.strip() or msg.content
        if msg.author.bot:
            content = (f"[Dispatched by fellow agent {msg.author.display_name} — its request is "
                       f"below. Reply with the result. Only @mention another agent if you need "
                       f"them to act; never mention one just to acknowledge.]\n{content}")
        return content

    async def on_message(self, msg: discord.Message):
        if msg.author.id == getattr(self.user, "id", None):
            return
        if not msg.content.strip() and not msg.attachments:
            return
        # Mention dispatch: @mentioning a profile bot (user OR managed role) targets
        # that profile directly. Mentions of non-profile bots stay with the personas.
        me = msg.guild.me if msg.guild else None
        my_roles = {r.id for r in getattr(me, "roles", [])}
        mentions_me = (self.user in msg.mentions
                       or any(r.managed and r.id in my_roles for r in msg.role_mentions))
        if msg.author.bot:
            # inter-agent dispatch, same rules as dev_bot: trusted fleet bots only,
            # only when they @mention this profile; per-channel cap breaks loops
            if msg.author.id not in TRUSTED_BOT_IDS or not mentions_me:
                return
            if not self.shared.bot_dispatch_ok(msg.channel.id):
                return
        elif msg.author.id not in ALLOWED_USERS:
            return
        if (any(m.bot for m in msg.mentions) or any(r.managed for r in msg.role_mentions)) \
                and not mentions_me:
            return
        chan_id = self.resolve_channel()
        if chan_id is None:
            return
        # Follow-up inside a thread under #general
        if isinstance(msg.channel, discord.Thread) and msg.channel.parent_id == chan_id:
            entry = self.shared.sessions.get(str(msg.channel.id)) or {}
            owner = entry.get("profile", ROUTER_KEY)
            if mentions_me:
                resume = ((entry.get("sessions") or {}).get(self.key)
                          or (entry.get("session") if owner == self.key else None))
            elif self.key == owner:
                resume = entry.get("session")
            else:
                return
            content = self.strip_mention(msg, self.user, my_roles) if mentions_me else msg.content
            prompt = with_attachments(content, await save_attachments(msg))
            asyncio.create_task(handle_task(self.shared, self.key, msg.channel, prompt, resume))
            return
        # New task in #general: mentioned profile takes it directly; otherwise the
        # router client classifies + hands off
        if msg.channel.id == chan_id:
            if mentions_me:
                asyncio.create_task(self.dispatch_new(msg, key=self.key))
            elif self.key == ROUTER_KEY:
                asyncio.create_task(self.dispatch_new(msg))


async def main():
    load_profiles()
    shared = Shared()
    for key in PROFILES:
        shared.clients[key] = GeneralAgent(key, shared)
    await asyncio.gather(*(shared.clients[k].start(PROFILES[k]["token"]) for k in PROFILES))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
