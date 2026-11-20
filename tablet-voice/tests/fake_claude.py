#!/usr/bin/env python3
"""tests/fake_claude.py: stand-in for `claude -p ... --input-format stream-json --output-format stream-json` (spec 16).

Speaks the same protocol as the real CLI: {"type": "user"} lines in; out, per message, a system init line (first
message only), an assistant line calling StructuredOutput, its tool result and a {"type": "result"} event whose
structured_output holds the answer. Synthetic answers from a few keywords; it never calls anything.

Mode: the words in the file named by FAKE_CLAUDE_MODE_FILE (read at start and again for every message), else
FAKE_CLAUDE_MODE, else "ok". An optional second word is the answer delay in seconds (default 0.05).
  ok         answer from keywords in the Transcript line ("how many" counts the Calendar and Open tasks lines)
  slow       sleep FAKE_CLAUDE_SLOW_S (default 8) first, then answer
  malformed  a non-JSON line, then a result with no structured_output and a text that is not JSON
  schema     a result whose object breaks the schema (intent "weather")
  error      an error result (is_error true), like an expired token or a usage limit
  crash      exit 3 at start, before reading anything
  die        exit 1 after reading the message, nothing written
  silent     read the message, never answer (stdin EOF still ends it)
  hang       never answer, ignore stdin EOF and SIGTERM (only SIGKILL ends it)
Ghost turn: when the file named by FAKE_CLAUDE_GHOST_FILE exists at start, this process deletes it (so only one
process ghosts) and, FAKE_CLAUDE_GHOST_S (default 0.3) seconds later, writes a whole unsolicited turn (task.add
"buy eggs") without any message, like a spare another agent spoke to while it was idle (spec 16 review).
FAKE_CLAUDE_GHOST_ALWAYS=1 makes every process do it (a CLI that always writes first).
Every start, message and exit goes to FAKE_CLAUDE_LOG (when set) as one JSON line with the pid. The argv is checked
for the flags llm.py must pass; a missing one exits 2 before anything else.
"""
import json
import os
import signal
import sys
import time

PID = os.getpid()


def log(**kw):
    path = os.environ.get("FAKE_CLAUDE_LOG")
    if path:
        with open(path, "a") as f:
            f.write(json.dumps({"pid": PID, "t": round(time.time(), 3), **kw}) + "\n")


def mode():
    words = []
    path = os.environ.get("FAKE_CLAUDE_MODE_FILE")
    if path:
        try:
            with open(path) as f:
                words = f.read().split()
        except OSError:
            pass
    words = words or os.environ.get("FAKE_CLAUDE_MODE", "ok").split()
    return words[0], float(words[1]) if len(words) > 1 else 0.05


def argv_problems(argv):
    out = []

    def after(flag):
        return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else None
    for flag in ("-p", "--verbose", "--no-session-persistence", "--strict-mcp-config", "--disable-slash-commands"):
        if flag not in argv:
            out.append(f"missing {flag}")
    for flag, want in (("--input-format", "stream-json"), ("--output-format", "stream-json"), ("--tools", ""),
                       ("--setting-sources", ""), ("--mcp-config", '{"mcpServers":{}}')):
        if after(flag) != want:
            out.append(f"{flag} is {after(flag)!r}")
    try:
        schema = json.loads(after("--json-schema") or "")
        if schema.get("additionalProperties") is not False or len(schema.get("required", [])) != 7:
            out.append("schema not strict")
    except ValueError:
        out.append("--json-schema not JSON")
    if not after("--model") or not after("--effort") or not after("--system-prompt"):
        out.append("model, effort or system prompt missing")
    return out


def emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def answer(content):
    o = dict.fromkeys(("intent", "title", "list", "due", "value", "query", "say"), "")
    counts, sec = {"ev": 0, "tk": 0}, None
    said = ""
    for line in content.split("\n"):
        if line.startswith("Calendar"):
            sec = "ev"
        elif line.startswith("Open tasks"):
            sec = "tk"
        elif line.startswith("Transcript: "):
            sec, said = None, line[len("Transcript: "):].lower()
        elif line.startswith("- ") and sec:
            counts[sec] += 1
    if "how many" in said:
        o.update(intent="answer", say=f"I see {counts['ev']} events and {counts['tk']} open tasks.")
    elif "milk" in said and "done" in said:
        o.update(intent="task.complete", query="buy milk")
    elif "milk" in said:
        o.update(intent="task.add", title="Buy milk", list="shopping" if "shopping" in said else "personal")
    elif "dark mode" in said:
        o.update(intent="theme", value="dark")
    elif "light mode" in said:
        o.update(intent="theme", value="light")
    elif "next" in said:
        o.update(intent="next.event")
    elif "never mind" in said:
        o.update(intent="cancel")
    else:
        o["intent"] = "none"
    return o


def turn(obj):
    emit({"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": "toolu_fake", "name": "StructuredOutput", "input": obj}]}, "session_id": "fake"})
    emit({"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "toolu_fake", "content": "Structured output provided successfully"}]}})
    emit({"type": "result", "subtype": "success", "is_error": False, "num_turns": 1, "result": "",
          "structured_output": obj, "session_id": "fake"})


def init():
    emit({"type": "system", "subtype": "init", "session_id": "fake", "tools": [], "mcp_servers": [], "model": "fake"})


def ghost():
    """A turn nobody here asked for (the reviewer's fake2.py ghost mode): it must never become an answer."""
    if os.environ.get("FAKE_CLAUDE_GHOST_ALWAYS") != "1":
        try:
            os.unlink(os.environ.get("FAKE_CLAUDE_GHOST_FILE"))   # claim it: one ghost per file
        except (OSError, TypeError):
            return False
    time.sleep(float(os.environ.get("FAKE_CLAUDE_GHOST_S", "0.3")))
    log(ev="ghost")
    init()
    turn({**dict.fromkeys(("intent", "title", "list", "due", "value", "query", "say"), ""),
          "intent": "task.add", "title": "buy eggs", "list": "personal"})
    return True


def reply(m, content, first):
    if first:
        init()
    if m == "malformed":
        sys.stdout.write("Warning: this line is not JSON {\n")
        emit({"type": "result", "subtype": "success", "is_error": False, "num_turns": 1,
              "result": "Sure, I will add that for you.", "session_id": "fake"})
        return
    if m == "error":
        emit({"type": "result", "subtype": "success", "is_error": True, "num_turns": 1,
              "result": "Invalid bearer token", "session_id": "fake"})
        return
    obj = answer(content)
    if m == "schema":
        obj["intent"] = "weather"
    turn(obj)


def main():
    problems = argv_problems(sys.argv[1:])
    m, _ = mode()
    log(ev="start", mode=m, problems=problems, cwd=os.getcwd(), api_key="ANTHROPIC_API_KEY" in os.environ,  # pragma: allowlist secret
        config_dir=os.environ.get("CLAUDE_CONFIG_DIR"))
    if problems:
        print("fake_claude: " + "; ".join(problems), file=sys.stderr)
        return 2
    if m == "crash":
        print("fake_claude: crash on start", file=sys.stderr)
        return 3
    if m == "hang":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    first = not ghost()
    for raw in sys.stdin:
        msg = json.loads(raw)
        content = msg["message"]["content"]
        m, delay = mode()
        log(ev="msg", mode=m, content=content)
        if m == "die":
            return 1
        if m == "hang":
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            while True:
                time.sleep(3600)
        if m == "silent":
            for _ in sys.stdin:
                pass
            break
        time.sleep(float(os.environ.get("FAKE_CLAUDE_SLOW_S", "8")) if m == "slow" else delay)
        reply(m, content, first)
        first = False
    if mode()[0] == "hang":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        while True:
            time.sleep(3600)
    log(ev="exit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
