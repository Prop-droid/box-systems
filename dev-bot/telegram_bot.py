#!/usr/bin/env python3
"""telegram-agent: Telegram -> Claude Code sessions on the box.

Reuses dev_bot.py's engine (run_claude stream-json runner, sessions.json,
thread_title, tool_phrase) with a Telegram Bot API transport — plain urllib
long-polling, no third-party deps.

Two modes, both active when configured:
  PRIVATE CHAT (zero setup): any ALLOWED_USER_IDS user DMs the bot. One rolling
    session per user; /new starts a fresh session. This is the default surface.
  FORUM GROUP (optional, CHAT_ID set to a Topics-enabled supergroup): message in
    the General topic = new task -> the bot creates a forum topic + fresh
    session; message inside a topic = --resume of that topic's session.

Shared behavior: messages sent mid-run get a reaction ack, queue, and land in
the same session (terminal-style). Replies over ~12k chars ship as a .md
document instead of message spam. State: sessions.json (BOT_DIR).

Instance .env keys (in BOT_DIR):
  TELEGRAM_TOKEN=...        # required (@BotFather)
  ALLOWED_USER_IDS=123,456  # required; unset = setup mode (bot echoes ids)
  CHAT_ID=-100...           # optional forum supergroup id
  CLAUDE_CWD=/home/tomas
  SYSTEM_PROMPT_FILES=/a:/b # optional, same semantics as dev_bot
  MODEL=claude-fable-5

Group mode setup: group -> enable Topics -> add the bot as ADMIN with
"Manage Topics" (admins see all messages, so privacy mode doesn't matter).
Run: BOT_DIR=~/systems/tg-dev-bot ~/systems/dev-bot/venv/bin/python telegram_bot.py

Telegram-vs-Discord deltas: bots cannot see other bots' messages, so
inter-agent mention dispatch does NOT work over this transport — bot-to-bot
handoffs stay on the box / on Discord.
"""
import asyncio
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import dev_bot  # engine reuse; BOT_DIR env must point at THIS instance's dir

DROPS_DIR = Path.home() / "Downloads" / "telegram-drops"
MSG_LIMIT = 4000        # hard cap 4096; headroom for safety
DOC_THRESHOLD = 12000   # > ~3 messages -> send a .md document instead
QUEUED_REACTION = "✍"   # Telegram only allows emoji from its fixed reaction set

TELEGRAM_GUARDRAILS = (
    "You are dispatched from Tomas's Agentic OS Telegram bot for development, "
    "system-fix and infra tasks across his fleet (see the fleet-control skill). "
    "Rules: (1) Destructive or hard-to-reverse operations (rm -rf, disabling/"
    "removing services or crons, resets, dropping data) require an explicit "
    "confirmation BEFORE running - state the exact command and wait for "
    "the next message. (2) Never push to work-account (tomas-ejam) repos. "
    "(3) Reply Hermes-style: lead with what changed + proof, short; this lands "
    "in Telegram, so no giant walls of text. (4) If blocked on info only Tomas "
    "has, ask in one compact question."
)

START_TEXT = (
    "Developer bot online. Send a task as a plain message — it runs in a fresh "
    "Claude session that follow-up messages continue. /new starts a clean "
    "session. Attach files freely; long replies arrive as .md documents."
)


def _api(method: str, params: dict, http_timeout: float = 35) -> dict:
    token = os.environ["TELEGRAM_TOKEN"]
    data = urllib.parse.urlencode(
        {k: v if isinstance(v, str) else json.dumps(v)
         for k, v in params.items() if v is not None}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=data)
    with urllib.request.urlopen(req, timeout=http_timeout) as r:
        out = json.loads(r.read())
    if not out.get("ok"):
        raise RuntimeError(f"{method}: {out.get('error_code')} {out.get('description')}")
    return out["result"]


async def api(method: str, http_timeout: float = 35, **params):
    return await asyncio.to_thread(_api, method, params, http_timeout)


def _send_document(chat_id: int, thread_id: int | None, filename: str,
                   content: bytes, caption: str = ""):
    token = os.environ["TELEGRAM_TOKEN"]
    boundary = uuid.uuid4().hex
    fields = {"chat_id": str(chat_id), "caption": caption[:1000]}
    if thread_id:
        fields["message_thread_id"] = str(thread_id)
    body = b""
    for k, v in fields.items():
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"'
                 f"\r\n\r\n{v}\r\n").encode()
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="document"; '
             f'filename="{filename}"\r\nContent-Type: text/markdown\r\n\r\n').encode()
    body += content + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendDocument", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.loads(r.read())
    if not out.get("ok"):
        raise RuntimeError(f"sendDocument: {out.get('description')}")


def _download_file(file_path: str, dest: Path):
    token = os.environ["TELEGRAM_TOKEN"]
    with urllib.request.urlopen(
            f"https://api.telegram.org/file/bot{token}/{file_path}", timeout=120) as r:
        dest.write_bytes(r.read())


class Ctx:
    """Where a task lives: chat + optional forum thread + session-map key."""
    def __init__(self, chat_id: int, thread_id: int | None, key: str):
        self.chat_id = chat_id
        self.thread_id = thread_id
        self.key = key


class Board:
    """One Telegram message per task, edited in place — port of dev_bot.StatusBoard."""
    MIN_EDIT_GAP = 3.0  # Telegram edit rate limits are tighter than Discord's
    MAX_TODOS = 8
    MARKS = {"completed": "☑", "in_progress": "▸", "pending": "◻"}

    def __init__(self, ctx: Ctx):
        self.ctx = ctx
        self.msg_id: int | None = None
        self.current = "Starting…"
        self.todos: list[dict] = []
        self.steps = 0
        self.started = time.monotonic()
        self._last_edit = 0.0
        self._last_text = ""
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
            lines.append(f"{mark} {dev_bot.snippet(td.get('content', ''), 60)}")
        if len(self.todos) > self.MAX_TODOS:
            lines.append(f"… +{len(self.todos) - self.MAX_TODOS} more")
        if not self._done:
            lines.append(f"{self._counter()} · {self._elapsed()}")
        return "\n".join(lines)[:MSG_LIMIT]

    async def _push(self, header: str | None = None):
        header = header or f"⏳ {self.current}"
        text = self._render(header)
        if text == self._last_text:
            return
        try:
            if self.msg_id is None:
                m = await api("sendMessage", chat_id=self.ctx.chat_id,
                              message_thread_id=self.ctx.thread_id, text=text)
                self.msg_id = m["message_id"]
            else:
                await api("editMessageText", chat_id=self.ctx.chat_id,
                          message_id=self.msg_id, text=text)
            self._last_text = text
            self._last_edit = time.monotonic()
        except (RuntimeError, OSError) as e:
            print(f"WARN: status edit failed: {e}", flush=True)

    async def _delayed_push(self, delay: float):
        await asyncio.sleep(delay)
        await self._push()

    async def on_block(self, block: dict):
        t = block.get("type")
        if t == "text":
            s = dev_bot.snippet(block.get("text", ""), 100)
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
                    self.current = dev_bot.snippet(active.get("activeForm", ""), 80) + "…"
            else:
                self.current = dev_bot.tool_phrase(name, inp)
        else:
            return
        gap = time.monotonic() - self._last_edit
        if gap >= self.MIN_EDIT_GAP:
            await self._push()
        elif self._pending is None or self._pending.done():
            self._pending = asyncio.create_task(self._delayed_push(self.MIN_EDIT_GAP - gap))

    async def finish(self, icon: str):
        if self._pending and not self._pending.done():
            self._pending.cancel()
        self._done = True
        word = {"✅": "Done", "❌": "Failed", "⏱️": "Timed out"}.get(icon, "Done")
        await self._push(f"{icon} {word} · {self._counter()} · {self._elapsed()}")


class TgAgent:
    def __init__(self):
        self.sessions = dev_bot.load_sessions()
        self.locks: dict[str, asyncio.Lock] = {}
        self.queues: dict[str, list[str]] = {}
        self.chat_id = int(os.environ.get("CHAT_ID", "0") or 0)
        self.allowed = {int(x) for x in
                        os.environ.get("ALLOWED_USER_IDS", "").replace(" ", "").split(",") if x}
        self.offset = 0
        self.setup_replied: set[int] = set()

    # --- helpers -----------------------------------------------------------
    def lock_for(self, key: str) -> asyncio.Lock:
        return self.locks.setdefault(key, asyncio.Lock())

    def queue_for(self, key: str) -> list[str]:
        return self.queues.setdefault(key, [])

    def system_prompt(self) -> str:
        sp = dev_bot.system_prompt()
        return TELEGRAM_GUARDRAILS if sp == dev_bot.DEFAULT_GUARDRAILS else sp

    def persist_chat_id(self, cid: int):
        """Adopt a group as the bot's forum group and write it back to .env."""
        self.chat_id = cid
        lines = dev_bot.ENV.read_text().splitlines()
        if any(l.startswith("CHAT_ID=") for l in lines):
            lines = [f"CHAT_ID={cid}" if l.startswith("CHAT_ID=") else l for l in lines]
        else:
            lines.append(f"CHAT_ID={cid}")
        dev_bot.ENV.write_text("\n".join(lines) + "\n")
        print(f"[adopt] group {cid} persisted to .env", flush=True)

    async def save_attachments(self, msg: dict) -> list[str]:
        """Download document/photo/voice/video/audio to DROPS_DIR; returns paths."""
        items: list[tuple[str, str]] = []  # (file_id, name)
        if d := msg.get("document"):
            items.append((d["file_id"], d.get("file_name") or "file"))
        if p := msg.get("photo"):
            items.append((p[-1]["file_id"], "photo.jpg"))  # last = largest size
        for key, name in (("voice", "voice.ogg"), ("audio", "audio.mp3"),
                          ("video", "video.mp4"), ("video_note", "video_note.mp4")):
            if f := msg.get(key):
                items.append((f["file_id"], f.get("file_name") or name))
        paths: list[str] = []
        if not items:
            return paths
        DROPS_DIR.mkdir(parents=True, exist_ok=True)
        for file_id, name in items:
            try:
                info = await api("getFile", file_id=file_id)
                safe = re.sub(r"[^\w.\- ]", "_", name).strip() or "file"
                dest = DROPS_DIR / f"{msg['message_id']}-{safe}"
                await asyncio.to_thread(_download_file, info["file_path"], dest)
                paths.append(str(dest))
            except (RuntimeError, OSError) as e:  # >20MB files fail getFile — report, don't die
                print(f"WARN: attachment save failed ({name}): {e}", flush=True)
        return paths

    @staticmethod
    def with_attachments(content: str, paths: list[str]) -> str:
        if not paths:
            return content
        listing = "\n".join(paths)
        return (f"{content}\n\n[Attachments from this Telegram message, saved on the box:\n"
                f"{listing}\nUse these files as part of the task.]")

    async def send_reply(self, ctx: Ctx, text: str):
        text = text.strip() or "(no output)"
        if len(text) > DOC_THRESHOLD:
            head = dev_bot.snippet(text, 900)
            await asyncio.to_thread(_send_document, ctx.chat_id, ctx.thread_id,
                                    "reply.md", text.encode(), f"📄 Full reply attached. {head}")
            return
        while text:
            if len(text) <= MSG_LIMIT:
                await api("sendMessage", chat_id=ctx.chat_id,
                          message_thread_id=ctx.thread_id, text=text)
                break
            window = text[:MSG_LIMIT]
            cut = window.rfind("\n\n")
            if cut < MSG_LIMIT // 2:
                cut = window.rfind("\n")
            if cut < MSG_LIMIT // 2:
                cut = window.rfind(" ")
            if cut < MSG_LIMIT // 2:
                cut = MSG_LIMIT
            await api("sendMessage", chat_id=ctx.chat_id,
                      message_thread_id=ctx.thread_id, text=text[:cut].rstrip())
            text = text[cut:].lstrip()

    # --- task flow ---------------------------------------------------------
    async def enqueue(self, ctx: Ctx, prompt: str, msg_id: int | None = None):
        self.queue_for(ctx.key).append(prompt)
        if self.lock_for(ctx.key).locked():
            if msg_id:
                try:
                    await api("setMessageReaction", chat_id=ctx.chat_id, message_id=msg_id,
                              reaction=[{"type": "emoji", "emoji": QUEUED_REACTION}])
                except (RuntimeError, OSError):
                    pass
            return
        asyncio.create_task(self.drain(ctx))

    async def drain(self, ctx: Ctx):
        async with self.lock_for(ctx.key):
            q = self.queue_for(ctx.key)
            while q:
                prompt = "\n\n".join(q)
                q.clear()
                resume = self.sessions.get(ctx.key)
                if resume and dev_bot.session_context_tokens(resume) > dev_bot.COMPACT_AT:
                    # compaction fires the PreCompact memory-flush hook, so nothing is lost
                    try:
                        await self.send_reply(
                            ctx, "🗜️ Session context near the 529 wedge zone — saving durable "
                                 "knowledge to memory, then compacting (~2-4 min)…")
                        await dev_bot.compact_session(resume)
                    except (RuntimeError, OSError):
                        pass
                try:
                    board = Board(ctx)
                    reply, session_id = await dev_bot.run_claude(
                        prompt, resume, on_block=board.on_block,
                        sys_prompt=self.system_prompt())
                    await board.finish("⏱️" if reply.startswith("⏱️")
                                       else "❌" if reply.startswith("❌") else "✅")
                    if session_id:
                        self.sessions[ctx.key] = session_id
                        dev_bot.save_sessions(self.sessions)
                    await self.send_reply(ctx, reply)
                except Exception as e:
                    print(f"ERROR: drain({ctx.key}): {e!r}", flush=True)
                    try:
                        await api("sendMessage", chat_id=ctx.chat_id,
                                  message_thread_id=ctx.thread_id,
                                  text=f"❌ Task crashed: {e!r}"[:MSG_LIMIT]
                                       + "\nReply here to retry.")
                    except Exception:
                        pass
        if self.queue_for(ctx.key):
            asyncio.create_task(self.drain(ctx))

    async def handle(self, msg: dict):
        uid = (msg.get("from") or {}).get("id")
        chat = msg.get("chat") or {}
        text = msg.get("text") or msg.get("caption") or ""
        print(f"[msg] chat={chat.get('id')} type={chat.get('type')} uid={uid} "
              f"text={dev_bot.snippet(text, 40)!r}", flush=True)
        if (msg.get("from") or {}).get("is_bot"):
            return
        # Setup mode: no allowed users configured — echo the ids for .env, once per chat.
        if not self.allowed:
            if chat.get("id") not in self.setup_replied:
                self.setup_replied.add(chat.get("id"))
                print(f"[setup] chat={chat.get('id')} type={chat.get('type')} user={uid}", flush=True)
                try:
                    await api("sendMessage", chat_id=chat["id"],
                              text=("Setup mode — add to BOT_DIR/.env:\n"
                                    f"ALLOWED_USER_IDS={uid}\n"
                                    f"CHAT_ID={chat.get('id')}  # only if this is the forum group\n"
                                    "then restart the service."))
                except (RuntimeError, OSError):
                    pass
            return
        # Group -> supergroup migration (e.g. Topics enabled): follow the new id.
        if (new_id := msg.get("migrate_to_chat_id")) and chat.get("id") == self.chat_id:
            self.persist_chat_id(new_id)
            return
        if uid not in self.allowed:
            return
        private = chat.get("type") == "private"
        if not private:
            if (self.chat_id == 0 and chat.get("type") in ("group", "supergroup")):
                # No group configured yet — adopt the first group an allowed user
                # messages from, then keep processing this message normally.
                self.persist_chat_id(chat["id"])
                try:
                    gc = await api("getChat", chat_id=chat["id"])
                    note = ("topic-per-task mode" if gc.get("is_forum") else
                            "Topics are OFF — running as one rolling session; enable "
                            "Topics in group settings for a topic per task")
                    await api("sendMessage", chat_id=chat["id"],
                              text=f"✅ Group linked ({note}).")
                except (RuntimeError, OSError):
                    pass
            elif chat.get("id") != self.chat_id:
                return
        if not text.strip() and not any(msg.get(k) for k in
                                        ("document", "photo", "voice", "audio", "video", "video_note")):
            return

        # --- private chat: one rolling session per user, /new resets -------
        if private:
            ctx = Ctx(chat["id"], None, f"dm{uid}")
            cmd = text.strip().lower()
            if cmd.startswith("/start"):
                await api("sendMessage", chat_id=ctx.chat_id, text=START_TEXT)
                return
            if cmd.startswith("/new"):
                self.sessions.pop(ctx.key, None)
                dev_bot.save_sessions(self.sessions)
                rest = text.strip()[4:].strip()
                await api("sendMessage", chat_id=ctx.chat_id, text="🆕 Fresh session.")
                if not rest:
                    return
                text = rest
            content = self.with_attachments(text, await self.save_attachments(msg))
            await self.enqueue(ctx, content, msg["message_id"])
            return

        # --- forum group: topic per task -----------------------------------
        files = await self.save_attachments(msg)
        content = self.with_attachments(text, files)
        thread_id = msg.get("message_thread_id")
        if thread_id:  # inside an existing topic = follow-up (or fresh session in a manual topic)
            await self.enqueue(Ctx(self.chat_id, thread_id, str(thread_id)), content,
                               msg["message_id"])
            return
        # General topic = new task -> create a forum topic
        fallback = (text.strip().replace("\n", " ")[:80]
                    or (Path(files[0]).name[:80] if files else "task"))
        name = await asyncio.to_thread(dev_bot.thread_title, text or fallback, fallback)
        try:
            topic = await api("createForumTopic", chat_id=self.chat_id, name=name[:128])
            thread_id = topic["message_thread_id"]
            await api("sendMessage", chat_id=self.chat_id, message_thread_id=thread_id,
                      text=f"📋 {dev_bot.snippet(text, 300) or fallback}")
        except (RuntimeError, OSError) as e:
            print(f"WARN: createForumTopic failed ({e}); replying in General", flush=True)
            thread_id = None  # degrade: single General-keyed session
        await self.enqueue(Ctx(self.chat_id, thread_id,
                               str(thread_id) if thread_id else "general"), content)

    # --- main loop ---------------------------------------------------------
    async def run(self):
        me = await api("getMe")
        mode = "SETUP MODE" if not self.allowed else \
            f"dm={sorted(self.allowed)} group={self.chat_id or 'off'}"
        print(f"telegram-agent ready as @{me.get('username')}; {mode}", flush=True)
        while True:
            try:
                updates = await api("getUpdates", http_timeout=60, offset=self.offset,
                                    timeout=50, allowed_updates=["message"])
            except (RuntimeError, OSError) as e:
                if "409" in str(e):
                    print("WARN: getUpdates 409 — another poller holds this token", flush=True)
                    await asyncio.sleep(15)
                else:
                    print(f"WARN: getUpdates: {e}", flush=True)
                    await asyncio.sleep(5)
                continue
            for up in updates:
                self.offset = up["update_id"] + 1
                if m := up.get("message"):
                    try:
                        await self.handle(m)
                    except Exception as e:
                        print(f"ERROR: handle: {e!r}", flush=True)


def main():
    dev_bot.load_env()
    if not os.environ.get("TELEGRAM_TOKEN"):
        sys.exit("TELEGRAM_TOKEN missing in .env")
    asyncio.run(TgAgent().run())


if __name__ == "__main__":
    main()
