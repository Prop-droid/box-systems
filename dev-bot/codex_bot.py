#!/usr/bin/env python3
"""channel-agent variant: a Discord channel -> OpenAI Codex CLI sessions on the box.

Same scaffolding as dev_bot.py (thread = session, sessions.json, StatusBoard),
but the engine is `codex exec --json` instead of `claude -p`. Auth comes from
~/.codex/auth.json (seeded from the Hermes ChatGPT-subscription OAuth tokens).

Instance .env keys (in BOT_DIR):
  DISCORD_TOKEN=...                      # required
  CHANNEL_NAME=qa                        # channel to watch
  CLAUDE_CWD=/home/tomas                 # cwd for codex sessions (name kept for parity)
  SYSTEM_PROMPT_FILES=/path/a:/path/b    # prepended to the FIRST prompt of a session
  MODEL=                                 # optional codex -m override; empty = CLI default

Codex has no --append-system-prompt, so guardrails are prepended to the first
message of each session only; resumes rely on the session carrying them.
"""
import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import dev_bot
from dev_bot import snippet

CODEX_BIN = os.path.expanduser("~/.npm-global/bin/codex")
TIMEOUT_S = dev_bot.TIMEOUT_S

# Bot-private durable memory, injected into each fresh session; the agent
# edits the file itself (it runs with full disk access).
MEMORY_FILE = dev_bot.BASE / "memory" / "MEMORY.md"

# Memory-compiler bridge: per-thread transcripts are flushed through the
# compiler's own flush.py so its slot locks / backpressure / extraction apply.
COMPILER_ROOT = Path.home() / ".tools" / "claude-memory-compiler"
TRANSCRIPTS_DIR = dev_bot.BASE / "transcripts"
MIN_TURNS_TO_FLUSH = 4      # 2 full exchanges, mirrors the compiler's gate
MIN_CHARS_TO_FLUSH = 1_500
MAX_LOADAVG_TO_SPAWN = 8.0
MAX_RUNNING_FLUSHES = 2


def memory_block() -> str:
    try:
        mem = MEMORY_FILE.read_text().strip()
    except OSError:
        mem = "(empty)"
    return (
        f"<memory>\nYou have a private persistent memory file: {MEMORY_FILE}\n"
        "Its current content is below. When this conversation teaches you something durable "
        "(a fact about Tomas or his systems, a recurring question's answer, a correction), "
        "edit that file yourself before finishing - one fact per line, keep it under 200 lines, "
        "prune stale lines. Do not mention the memory file in replies unless asked.\n\n"
        f"{mem}\n</memory>"
    )


def flush_to_compiler(session_id: str, prompt: str, reply: str):
    """Append this exchange to the thread transcript and, past the junk gate,
    hand it to the memory compiler's flush.py (same contract as its
    SessionEnd hook: <context_file.md> <session_id>). Best-effort."""
    TRANSCRIPTS_DIR.mkdir(exist_ok=True)
    tf = TRANSCRIPTS_DIR / f"{session_id}.md"
    with tf.open("a") as f:
        f.write(f"## Tomas\n{prompt}\n\n## QA (codex)\n{reply}\n\n")
    text = tf.read_text()
    turns = text.count("## ")
    if turns < MIN_TURNS_TO_FLUSH or len(text) < MIN_CHARS_TO_FLUSH:
        return
    scripts = COMPILER_ROOT / "scripts"
    if not (scripts / "flush.py").exists():
        return
    if os.getloadavg()[0] > MAX_LOADAVG_TO_SPAWN:
        return
    running = subprocess.run(["pgrep", "-fc", r"scripts/flush\.py"],
                             capture_output=True, text=True, timeout=5)
    if running.returncode == 0 and int(running.stdout.strip() or 0) >= MAX_RUNNING_FLUSHES:
        return
    ts = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    context_file = scripts / f"session-flush-{session_id}-{ts}.md"
    context_file.write_text(
        f"# Discord #qa session (Codex, QA bot)\n\n{text}", encoding="utf-8")
    subprocess.Popen(
        ["uv", "run", "--directory", str(COMPILER_ROOT), "python",
         str(scripts / "flush.py"), str(context_file), session_id],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
        env={**os.environ, "PATH": os.path.expanduser("~/.local/bin") + ":" + os.environ.get("PATH", "")},
    )


def codex_block(item: dict) -> dict | None:
    """Map a codex JSONL item to a claude-style content block for StatusBoard."""
    t = item.get("type")
    if t == "agent_message":
        return {"type": "text", "text": item.get("text", "")}
    if t == "command_execution":
        return {"type": "tool_use", "name": "Bash",
                "input": {"description": snippet(item.get("command", ""), 60)}}
    if t == "file_change":
        changes = item.get("changes") or []
        path = (changes[0].get("path", "") if changes else "")
        return {"type": "tool_use", "name": "Edit", "input": {"file_path": path}}
    if t == "web_search":
        return {"type": "tool_use", "name": "WebSearch",
                "input": {"query": item.get("query", "")}}
    if t == "mcp_tool_call":
        return {"type": "tool_use", "name": f"mcp__{item.get('server','?')}__{item.get('tool','?')}",
                "input": {}}
    return None  # reasoning etc.


async def run_codex(prompt: str, resume: str | None, on_block=None,
                    cwd: str | None = None, model: str | None = None,
                    sys_prompt: str | None = None) -> tuple[str, str | None]:
    """Streams codex work via on_block. Returns (reply_text, session_id)."""
    user_prompt = prompt
    if not resume:
        guard = sys_prompt or dev_bot.system_prompt()
        prompt = f"<instructions>\n{guard}\n</instructions>\n\n{memory_block()}\n\n{prompt}"
    cmd = [CODEX_BIN, "exec"]
    if resume:
        cmd += ["resume", resume]
    cmd += ["--json", "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox"]
    if not resume:  # resume restores cwd from the session; --cd is rejected there
        cmd += ["--cd", os.path.expanduser(cwd or os.environ.get("CLAUDE_CWD", "~"))]
    m = model or os.environ.get("MODEL", "")
    if m:
        cmd += ["-m", m]
    cmd += [prompt]
    env = dict(os.environ)
    env["PATH"] = os.path.expanduser("~/.npm-global/bin") + ":" + env.get("PATH", "")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        env=env,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=10 * 1024 * 1024,
    )
    stderr_task = asyncio.create_task(proc.stderr.read())
    loop = asyncio.get_running_loop()
    deadline = loop.time() + TIMEOUT_S
    last_message: str | None = None
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
            if t == "thread.started":
                session_id = ev.get("thread_id") or session_id
            elif t == "item.completed":
                item = ev.get("item") or {}
                if item.get("type") == "agent_message":
                    last_message = item.get("text") or last_message
                if on_block:
                    block = codex_block(item)
                    if block:
                        await on_block(block)
            elif t == "error":
                last_message = last_message or f"❌ codex error: {ev.get('message', '?')}"
    except asyncio.TimeoutError:
        proc.kill()
        stderr_task.cancel()
        return ("⏱️ Task timed out after 30 min. The session is saved - reply here to continue it.", session_id)
    rc = await proc.wait()
    err = await stderr_task
    if last_message is None:
        tail = (err or b"").decode(errors="replace")[-800:]
        return (f"❌ codex exited {rc}:\n```\n{tail or '(no output)'}\n```", session_id)
    if session_id:
        try:
            flush_to_compiler(session_id, user_prompt, last_message)
        except Exception as e:
            print(f"WARN: compiler flush failed: {e}", flush=True)
    return (last_message or "(empty result)", session_id)


def main():
    dev_bot.load_env()
    dev_bot.run_claude = run_codex  # handle_task resolves this at call time
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        sys.exit("DISCORD_TOKEN missing in .env")
    dev_bot.ChannelAgent(os.environ.get("CHANNEL_NAME", "qa")).run(token)


if __name__ == "__main__":
    main()
