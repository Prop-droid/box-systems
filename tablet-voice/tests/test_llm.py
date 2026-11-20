#!/usr/bin/env python3
"""tests/test_llm.py: the Opus layer (spec 16) with a fake claude: no network, no subscription use.

Part 1, pure: the mapping table (every intent, empty and long titles, bad enums, broken objects), the answer cap,
the schema and argv, the user message (the live 22-event spread whole, cuts at whole days named in the header, a
first day over the cap, the task cap, cut titles marked, no data), the result parser, server.understand() with a stub
(off, skip, used, timeout, invalid, error, the prefetched data, a prefetch still running: no wait), the decision rows
for "answer", the answer action, the logged intent, the journal view and the VOICE_LLM config.
Part 2, WarmClaude with tests/fake_claude.py: happy path, the spare recycled after use, timeout, malformed and
schema-breaking output (invalid), an error result and a dying process (error), crash at start and a missing binary
(respawn, backoff logged once, recovery), the idle-exit rule, the pause file, the cold path, recycling by age, a second ask while the
first runs, a spare that writes while idle (retired unused, never an answer; a CLI that always does: backoff), the
child environment (its own config dir, mode 700), shutdown with no child left (a SIGTERM-proof child too).
Part 3 (--server DIR): server.py on the test ports (dash 18765, voice 18766) with VOICE_LLM=claude and the fake:
the Opus intent used and logged next to the rules intent, the child's own config dir, an answer built from the
prefetched /api/data, the wake rules after the choice, skip on an unaddressed wake, timeout, pause and error fall
back to the rules, selftest.py on the Opus path, no child after stop, VOICE_LLM=off spawning nothing, and a hung
dashboard with Opus on (test_server.py H18 and H19: the ask never waits for the data).

  .venv/bin/python tests/test_llm.py                               # parts 1 and 2, about a minute
  timeout 900 .venv/bin/python tests/test_llm.py --server DIR      # all three parts
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import types
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
os.environ.setdefault("VOICE_STAGE", "skeleton")
os.environ.pop("VOICE_LLM", None)
import actions  # noqa: E402
import llm  # noqa: E402
import server  # noqa: E402
from fake_dash import fixture  # noqa: E402

FAKE = HERE / "fake_claude.py"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append({"name": name, "ok": bool(ok), "detail": str(detail)[:400]})
    print(f"{'PASS' if ok else 'FAIL'} {name}{': ' + str(detail)[:300] if detail and not ok else ''}", flush=True)


def obj(**kw):
    return {**dict.fromkeys(llm.FIELDS, ""), **kw}


# ------------------------------------------------------------------ part 1: pure

def part1_mapping():
    add = {"intent": "task.add", "list": "personal", "due": None}
    T = [  # name, object, expected to_intent()
        ("task.add", obj(intent="task.add", title="Buy milk", list="personal"), {**add, "title": "buy milk"}),
        ("task.add: default list, due, spaces collapsed", obj(intent="task.add", title="  call   the dentist ", due="tomorrow"),
         {**add, "title": "call the dentist", "due": "tomorrow"}),
        ("task.add: shopping passes through (D7 refuses it in actions)", obj(intent="task.add", title="eggs", list="shopping"),
         {**add, "title": "eggs", "list": "shopping"}),
        ("task.add: an acronym keeps its case", obj(intent="task.add", title="IKEA return", list="work"),
         {**add, "title": "IKEA return", "list": "work"}),
        ("task.add: 120 characters", obj(intent="task.add", title="a" * 120), {**add, "title": "a" * 120}),
        ("task.add: empty title -> no intent", obj(intent="task.add", title="   "), {"intent": None}),
        ("task.add: 121 characters -> no intent", obj(intent="task.add", title="b" * 121), {"intent": None}),
        ("next.event (say ignored)", obj(intent="next.event", say="x"), {"intent": "next.event"}),
        ("schedule.tomorrow", obj(intent="schedule.tomorrow"), {"intent": "schedule.tomorrow"}),
        ("theme", obj(intent="theme", value="light"), {"intent": "theme", "value": "light"}),
        ("theme without a value -> no intent", obj(intent="theme"), {"intent": None}),
        ("task.complete", obj(intent="task.complete", query="buy milk"), {"intent": "task.complete", "query": "buy milk"}),
        ("task.complete without a query -> no intent", obj(intent="task.complete"), {"intent": None}),
        ("answer", obj(intent="answer", say="Dentist is tomorrow at 14:30."), {"intent": "answer", "say": "Dentist is tomorrow at 14:30."}),
        ("answer without text -> no intent", obj(intent="answer", say=" "), {"intent": None}),
        ("cancel", obj(intent="cancel"), {"intent": "cancel"}),
        ("none", obj(intent="none", title="ignored"), {"intent": None}),
        ("bad enum: intent weather -> invalid", obj(intent="weather"), None),
        ("bad enum: list groceries -> invalid", obj(intent="task.add", title="eggs", list="groceries"), None),
        ("bad enum: due monday -> invalid", obj(intent="task.add", title="x", due="monday"), None),
        ("bad enum: value night -> invalid", obj(intent="theme", value="night"), None),
        ("missing key -> invalid", {k: v for k, v in obj(intent="none").items() if k != "say"}, None),
        ("extra key -> invalid", {**obj(intent="none"), "confidence": "high"}, None),
        ("a number for the title -> invalid", {**obj(intent="task.add"), "title": 5}, None),
        ("null -> invalid", None, None),
        ("a list -> invalid", [], None),
    ]
    bad = [(n, llm.to_intent(o), want) for n, o, want in T if llm.to_intent(o) != want]
    check(f"mapping table, {len(T)} rows (every intent, empty and long title, bad enums, broken objects)", not bad, bad)
    for i in llm.INTENTS:
        if i not in {json.dumps(o.get("intent")).strip('"') for _, o, _ in T if isinstance(o, dict)}:
            check(f"mapping table covers {i}", False)
    long = llm.to_intent(obj(intent="answer", say="word " * 80))
    check("answer capped at 200 characters on a word boundary", len(long["say"]) <= 200 and long["say"].endswith("."),
          len(long["say"]))
    s = llm.SCHEMA
    check("schema: seven required string fields, no others, the enums of spec 16",
          s["additionalProperties"] is False and s["required"] == list(llm.FIELDS)
          and s["properties"]["intent"]["enum"] == ["task.add", "next.event", "schedule.tomorrow", "theme", "task.complete",
                                                    "answer", "cancel", "none"]
          and s["properties"]["list"]["enum"] == ["", "personal", "work", "shopping"]
          and s["properties"]["due"]["enum"] == ["", "today", "tomorrow"]
          and s["properties"]["value"]["enum"] == ["", "dark", "light", "auto"]
          and all(s["properties"][k] == {"type": "string"} for k in ("title", "query", "say")))
    a = llm.claude_args("claude-opus-5-5", "low")
    check("argv: the trimmed warm-spare flags of spec 16 and --json-schema with the schema",
          a[:5] == ["-p", "--model", "claude-opus-5-5", "--effort", "low"] and json.loads(a[a.index("--json-schema") + 1]) == s
          and a[a.index("--tools") + 1] == "" and a[a.index("--setting-sources") + 1] == ""
          and a[-5:] == ["--input-format", "stream-json", "--output-format", "stream-json", "--verbose"]
          and "--bare" not in a, a)


def part1_message():
    data = fixture()
    now = server.dt.datetime(2026, 11, 6, 14, 5).astimezone()
    m = llm.build_message("Hey Jarvis,\nwhen is the dentist?", data, now)
    lines = m.split("\n")
    ev = [x for x in lines if x.startswith("- ") and ("Today" in x or "Tomorrow" in x)]
    check("message: time first, every fixture event and task, the transcript on one last line",
          lines[0] == "Now: Friday 06 November 2026, 14:05" and len(ev) == len(data["events"])
          and "- PERSONAL: Buy milk, due today" in lines and "- Work: Renew passport, due tomorrow" in lines
          and "- Work: Tax return 2026" in lines and lines[-1] == "Transcript: Hey Jarvis, when is the dentist?", m)
    labels = ["Today", "Tomorrow", "Sun Nov 08", "Wed Nov 11", "Thu Nov 12"]
    keys = ["2026-11-06", "2026-11-07", "2026-11-08", "2026-11-11", "2026-11-12"]

    def spread(per):
        return [{"time": f"{8 + j // 2:02d}:{j % 2 * 30:02d}", "title": f"Event {i}.{j}", "daylabel": labels[i],
                 "daykey": keys[i]} for i, n in enumerate(per) for j in range(n)]
    m = llm.build_message("what do I have on Thursday", {"events": spread((2, 5, 4, 6, 5)), "tasks": {}}, now)
    check("message: the review's live spread (22 events over 5 days) is listed whole, Thursday's 5 included, no cut",
          m.count("\n- ") == 22 and m.count("- Thu Nov 12, ") == 5 and "Calendar (today and the next 6 days):" in m
          and "cut short" not in m, m)
    per = (10, 12, 9, 8, 11)                       # the cap (40) falls inside Thursday
    m = llm.build_message("x", {"events": spread(per), "tasks": {}}, now)
    n_whole = sum(per[:4])
    check(f"message: {sum(per)} events: whole days only ({n_whole} listed, none of Thursday), the header names the first "
          "day left out and the count",
          n_whole < llm.MAX_EVENTS < n_whole + per[4] and m.count("\n- ") == n_whole and "- Thu Nov 12, " not in m
          and f"Calendar, cut short: every event before Thu Nov 12 is listed; Thu Nov 12 and later days are not shown "
              f"({per[4]} more events):" in m, m.split("\n")[1])
    m = llm.build_message("x", {"events": spread((3, 50)), "tasks": {}}, now)
    check("message: the cut falls on tomorrow: today listed, 'every event before tomorrow is listed'",
          m.count("\n- ") == 3 and "every event before tomorrow is listed; tomorrow and later days are not shown (50 more" in m,
          m.split("\n")[1])
    big = [{"time": "09:00", "title": f"E{i}", "daylabel": "Today", "daykey": keys[0]} for i in range(llm.MAX_EVENTS + 5)]
    m = llm.build_message("x", {"events": big, "tasks": {}}, now)
    check("message: one day over the cap: the first MAX_EVENTS listed and the header says the rest is not shown",
          m.count("- Today, 09:00: E") == llm.MAX_EVENTS
          and f"only the first {llm.MAX_EVENTS} of {llm.MAX_EVENTS + 5} events are listed; the rest are not shown" in m)
    tasks = {"overdue": [{"title": f"T{i}", "list": "Work", "due": "2026-11-01"} for i in range(5)],
             "backlog": [{"title": f"B{i}", "list": "Personal"} for i in range(llm.MAX_TASKS + 10)]}
    m = llm.build_message("x", {"events": [], "tasks": tasks}, now)
    check("message: more open tasks than the cap: overdue first and saying so, the header gives the count left out",
          m.count("\n- ") == llm.MAX_TASKS and m.count("overdue (due 2026-11-01)") == 5
          and f"Open tasks, cut short: the first {llm.MAX_TASKS} of {llm.MAX_TASKS + 15} are listed" in m
          and "; 15 are not shown:" in m)
    m = llm.build_message("x", {"events": [], "tasks": {"backlog": [{"title": f"B{i}"} for i in range(llm.MAX_TASKS)]}}, now)
    check("message: exactly the cap is not a cut", "Open tasks:" in m and "cut short" not in m)
    t86, t120, t200 = "a" * 86, "b" * 120, ("word " * 40).strip()
    m = llm.build_message("x", {"events": [{"time": "09:00", "title": t200, "daylabel": "Today", "daykey": keys[0]}],
                                "tasks": {"backlog": [{"title": t86, "list": "Personal"}, {"title": t120, "list": "Work"}]}}, now)
    title = next(x for x in m.split("\n") if x.startswith("- Today")).split(": ", 1)[1]
    check("message: titles up to 120 characters whole (86 as the live one, 120); a longer one cut and ending in '...'",
          f"- Personal: {t86}" in m and f"- Work: {t120}" in m and len(title) <= llm.MAX_ITEM and title.endswith("...")
          and t200.startswith(title[:-3]), title)
    check("prompt: a question that needs what the message says is not shown is none",
          "the message says are not shown" in llm.SYSTEM_PROMPT)
    check("message: no data -> calendar and tasks not available", "Calendar and tasks: not available right now." in
          llm.build_message("x", None, now))


def part1_parse():
    o = obj(intent="cancel")
    check("parse: structured_output first", llm.parse_result({"structured_output": o, "result": "{}"}) == o)
    check("parse: the result text as JSON when there is no structured_output (code fences too)",
          llm.parse_result({"result": "```json\n" + json.dumps(o) + "\n```"}) == o)
    check("parse: text that is not JSON gives nothing", llm.parse_result({"result": "Sure, I will add that."}) is None)


async def part1_understand():
    loop = asyncio.get_running_loop()
    data = fixture()

    def sess(by="ptt", done=True, deadline=5.0):
        f = loop.create_future()
        if done:
            f.set_result({"ok": True, "data": data, "ms": 1.0, "err": None, "fast": False})
        return types.SimpleNamespace(by=by, prefetch=f, read_deadline=time.monotonic() + deadline)

    class Stub:
        def __init__(self, r=None, exc=None):
            self.r, self.exc, self.calls = r, exc, []

        async def ask(self, transcript, context, timeout):
            self.calls.append((transcript, context, timeout))
            if self.exc:
                raise self.exc
            return self.r

    text, rest = "Hey Jarvis, goodbye milk to my personal list.", "goodbye milk to my personal list"
    server.LLM = None
    it, info = await server.understand(sess(), text, rest, True, True, False)
    check("understand, VOICE_LLM off: rules, llm_fallback off", it == {"intent": None} and info["llm_fallback"] == "off"
          and info["llm_used"] is False and info["rules_intent"] == {"name": None}, info)
    ok = Stub({"obj": obj(intent="task.add", title="Buy milk", list="personal"), "why": None, "ms": 1100})
    server.LLM = ok
    it, info = await server.understand(sess(), text, rest, True, True, False)
    check("understand: Opus decides when valid (the rules found nothing here); data and transcript passed",
          it == {"intent": "task.add", "title": "buy milk", "list": "personal", "due": None} and info["llm_used"] is True
          and info["llm_intent"]["name"] == "task.add" and info["llm_ms"] == 1100 and info["llm_fallback"] is None
          and ok.calls[-1][0] == text and ok.calls[-1][1] is data and ok.calls[-1][2] == server.CFG.llm_timeout_ms / 1000, info)
    n = len(ok.calls)
    for label, args in (("junk", (True, True, True)), ("a wake with no name and a low openWakeWord score", (False, False, False))):
        it, info = await server.understand(sess(by="wake"), text, rest, *args)
        check(f"understand: skip on {label} (Opus not asked)", info["llm_fallback"] == "skip" and len(ok.calls) == n, info)
    it, info = await server.understand(sess(by="wake"), text, "", True, True, False)
    check("understand: skip when nothing follows the wake phrase", info["llm_fallback"] == "skip" and len(ok.calls) == n)
    it, info = await server.understand(sess(by="wake"), text, rest, False, True, False)
    check("understand: a wake confirmed by openWakeWord but no name in the transcript still asks Opus",
          info["llm_used"] is True and len(ok.calls) == n + 1)
    t0 = time.monotonic()
    it, info = await server.understand(sess(done=False, deadline=5.0), text, rest, True, True, False)
    el = time.monotonic() - t0
    check("understand: a prefetch still running -> Opus asked at once without data (no wait for the dashboard)",
          ok.calls[-1][1] is None and info["llm_used"] is True and el < 0.1 and "llm_data_wait_ms" not in server.TUNE,
          {"s": round(el, 3), "info": info})
    for label, how in (("failed", "fail"), ("raised", "raise"), ("cancelled", "cancel")):
        f = loop.create_future()
        if how == "fail":
            f.set_result({"ok": False, "data": None, "ms": 5000.0, "err": "timeout", "fast": False})
        elif how == "raise":
            f.set_exception(RuntimeError("boom"))
        else:
            f.cancel()
        ok.calls.append(("marker", "marker", 0))
        it, info = await server.understand(types.SimpleNamespace(by="ptt", prefetch=f, read_deadline=time.monotonic() + 5),
                                           text, rest, True, True, False)
        check(f"understand: a prefetch that {label} -> Opus asked without data", ok.calls[-1][1] is None
              and ok.calls[-1][0] == text and info["llm_used"] is True, info)
    rules_add = "add by milk to my personal list"
    for label, stub, why in (("timeout", Stub({"obj": None, "why": "timeout", "ms": 3500}), "timeout"),
                             ("an object that maps to nothing valid", Stub({"obj": obj(intent="weather"), "why": None, "ms": 900}), "invalid"),
                             ("an exception in ask()", Stub(exc=RuntimeError("boom")), "error"),
                             ("paused", Stub({"obj": None, "why": "paused", "ms": 0}), "paused")):
        server.LLM = stub
        it, info = await server.understand(sess(), rules_add, rules_add, True, True, False)
        check(f"understand: {label} -> the rules intent, llm_fallback {why}",
              it == {"intent": "task.add", "title": "buy milk", "list": "personal", "due": None} and info["llm_used"] is False
              and info["llm_fallback"] == why and info["rules_intent"]["title"] == "buy milk", info)
    server.LLM = None


def part1_server_bits():
    server.CFG.read_needs_wake_text = False
    T = [("ptt", "answer", False, False, False, "run"), ("wake", "answer", True, False, False, "run"),
         ("wake", "answer", False, True, False, "silent_reject"), ("wake", "answer", False, False, False, "silent_reject"),
         ("wake", "answer", True, True, True, "junk"), ("wake", "next.event", False, True, False, "run"),
         ("wake", "task.add", False, True, False, "refuse_wake_text"), ("wake", "task.add", True, False, False, "run")]
    bad = [(r, server.decide(*r[:5])) for r in T if server.decide(*r[:5]) != r[5]]
    check(f"decide: answer needs the name or a tap; other rows unchanged ({len(T)} rows)", not bad, bad)
    server.CFG.read_needs_wake_text = True
    check("decide: strict reads (D11) keep answer on the name", server.decide("wake", "answer", True, True, False) == "run"
          and server.decide("wake", "answer", False, True, False) == "silent_reject")
    server.CFG.read_needs_wake_text = False

    def boom(*a, **k):
        raise urllib.error.URLError("no network in this test")
    actions._http = boom
    r = actions.run("answer", {"say": "Dentist is tomorrow at 14:30."}, dry=False, dash="http://d", data_res=None,
                    deliverable=lambda: True, allow_complete=False)
    check("action answer: say and card are the Opus text, no dashboard call, logged by length only",
          r["ok"] and r["say"] == r["card"] == "Dentist is tomorrow at 14:30." and r["say_log"] is None and r["do"] == []
          and r["action"]["kind"] == "answer" and r["say_len"] == 29, r)
    r = actions.run("answer", {"say": ""}, dry=True, dash="http://d", data_res=None, deliverable=lambda: True, allow_complete=False)
    check("action answer with no text: the sorry line", r["say"] == actions.SORRY and not r["ok"])
    li = server._log_intent({"intent": "answer", "say": "Dentist is tomorrow at 14:30."})
    check("logged intent: an answer keeps its length only", li == {"name": "answer", "say_len": 29}, li)
    sess = {"ev": "session", "heard": "Hey Jarvis add by milk", "text": "add by milk", "say": "Would add buy milk to Personal.",
            "intent": {"name": "task.add", "title": "buy milk"}, "rules_intent": {"name": "task.add", "title": "buy milk"},
            "llm_intent": {"name": "task.add", "title": "buy milk"}, "llm_used": True, "llm_fallback": None, "llm_ms": 1150}
    jv = server.journal_view(sess)
    check("journal: rules_intent and llm_intent are names only; llm_used, llm_fallback, llm_ms kept",
          jv["intent"] == jv["rules_intent"] == jv["llm_intent"] == "task.add" and jv["llm_ms"] == 1150
          and jv["llm_used"] is True and "buy milk" not in json.dumps(jv), jv)
    keep = dict(os.environ)
    try:
        for k in [k for k in os.environ if k.startswith("VOICE_LLM")]:
            del os.environ[k]
        c = server.Cfg()
        check("config: VOICE_LLM unset -> off; Opus 5.5, effort low, 3500 ms, ~/.local/bin/claude, the usage-guard file",
              c.llm == "off" and c.llm_model == "claude-opus-5-5" and c.llm_effort == "low" and c.llm_timeout_ms == 3500
              and c.llm_bin == str(Path.home() / ".local/bin/claude") and c.llm_pause_file == Path.home() / ".claude/PAUSE_CLAUDE_BG")
        os.environ["VOICE_LLM"] = "claude"
        check("config: VOICE_LLM=claude", server.Cfg().llm == "claude")
        for k, v in (("VOICE_LLM", "gpt"), ("VOICE_LLM_TIMEOUT_MS", "100"), ("VOICE_LLM_EFFORT", "huge")):
            os.environ[k] = v
            try:
                server.Cfg()
                check(f"config: {k}={v} refused", False)
            except SystemExit as e:
                check(f"config: {k}={v} refused", k in str(e), e)
            os.environ.pop(k)
            os.environ["VOICE_LLM"] = "claude"
    finally:
        os.environ.clear()
        os.environ.update(keep)


# ------------------------------------------------------------------ part 2: WarmClaude with the fake

class Fake:
    def __init__(self, td, name, **env):
        self.log, self.modef, self.cfg = Path(td) / f"{name}.log", Path(td) / f"{name}.mode", Path(td) / f"{name}-cfg"
        self.env = {**os.environ, "FAKE_CLAUDE_LOG": str(self.log), "FAKE_CLAUDE_MODE_FILE": str(self.modef), **env}
        self.set("ok")

    def set(self, m):
        self.modef.write_text(m)

    def rows(self, ev=None):
        try:
            rows = [json.loads(x) for x in self.log.read_text().splitlines() if x.strip()]
        except OSError:
            rows = []
        return [r for r in rows if ev is None or r.get("ev") == ev]

    def pids(self):
        return sorted({r["pid"] for r in self.rows("start")})


def gone(pid):
    return not Path(f"/proc/{pid}").exists()


async def until(cond, limit=6.0):
    t0 = time.monotonic()
    while time.monotonic() - t0 < limit:
        if cond():
            return True
        await asyncio.sleep(0.05)
    return bool(cond())


def warm(fake, td=None, **kw):
    lines = []
    w = llm.WarmClaude(FAKE, env=fake.env, log=lines.append, pause_file=kw.pop("pause_file", None),
                       config_dir=kw.pop("config_dir", fake.cfg), **kw)
    w.lines = lines
    return w


async def spare_ready(w, fake, n_starts):
    """A spare that has started (the fake logged its start) and is still alive."""
    return await until(lambda: w.spare is not None and w.spare.alive() and len(fake.rows("start")) >= n_starts)


async def part2(td):
    data = fixture()
    # happy path, recycled after use, warm second ask
    f = Fake(td, "happy")
    w = warm(f)
    w.start()
    await spare_ready(w, f, 1)
    pid1 = w.spare.proc.pid
    r = await w.ask("Hey Jarvis, add by milk to my personal list.", data, 3.0)
    msgs = f.rows("msg")
    check("happy path: a checked object, no fallback, one message to the warm spare",
          r["why"] is None and llm.to_intent(r["obj"]) == {"intent": "task.add", "title": "buy milk", "list": "personal", "due": None}
          and len(msgs) == 1 and msgs[0]["pid"] == pid1 and r["ms"] < 1500, {"r": r, "msgs": len(msgs)})
    c = msgs[0]["content"] if msgs else ""
    check("the message carries the time, the calendar, the tasks and the raw transcript",
          c.startswith("Now: ") and "Mum's birthday" in c and "Buy milk powder for Ema" in c
          and c.endswith("Transcript: Hey Jarvis, add by milk to my personal list."), c[-120:])
    ok = await until(lambda: gone(pid1) and w.spare is not None and w.spare.proc.pid != pid1 and w.spare.alive(), 5)
    check("spare recycled after use: the used process exited and was reaped, a new spare runs", ok,
          {"pid1_gone": gone(pid1), "spare": w.spare and w.spare.proc.pid})
    await spare_ready(w, f, 2)
    pid2 = w.spare.proc.pid
    r = await w.ask("turn on dark mode", data, 3.0)
    check("the next ask uses the new spare", r["why"] is None and f.rows("msg")[-1]["pid"] == pid2
          and llm.to_intent(r["obj"]) == {"intent": "theme", "value": "dark"}, r)
    check("an asked process's own output never counts as idle output", "idle_output" not in w.counts and not w.lines,
          {"counts": w.counts, "lines": w.lines})
    await w.close()

    # timeout, then recovery
    f = Fake(td, "slow", FAKE_CLAUDE_SLOW_S="10")
    f.set("slow")
    w = warm(f)
    w.start()
    await spare_ready(w, f, 1)
    pid1 = w.spare.proc.pid
    t0 = time.monotonic()
    r = await w.ask("turn on dark mode", data, 1.0)
    el = time.monotonic() - t0
    check("timeout: why timeout at the deadline", r["why"] == "timeout" and r["obj"] is None and 0.95 <= el <= 1.5, {"r": r, "s": round(el, 2)})
    ok = await until(lambda: gone(pid1), 4.0)
    check("timeout: the slow process is finished (stdin closed, SIGTERM after 2 s) and reaped", ok and time.monotonic() - t0 < 4.5,
          round(time.monotonic() - t0, 2))
    f.set("ok")
    await spare_ready(w, f, 2)
    r = await w.ask("turn on dark mode", data, 3.0)
    check("after a timeout the next spare answers", r["why"] is None, r)
    await w.close()

    # malformed and schema-breaking output -> invalid; error result and a dying process -> error; then ok
    f = Fake(td, "bad")
    w = warm(f)
    w.start()
    got = []
    for i, m in enumerate(("malformed", "schema", "error", "die", "ok")):
        f.set(m)
        await spare_ready(w, f, i + 1)
        got.append((m, (await w.ask("add buy milk", data, 3.0))["why"]))
    check("malformed -> invalid, schema-breaking -> invalid, error result -> error, dying process -> error, then ok",
          got == [("malformed", "invalid"), ("schema", "invalid"), ("error", "error"), ("die", "error"), ("ok", None)]
          and w.fails == 0 and not w.lines, got)
    await w.close()

    # crash at start -> respawn, backoff logged once, recovery after the backoff
    f = Fake(td, "crash")
    f.set("crash")
    w = warm(f, backoff_s=2.0)
    w.start()
    await until(lambda: w.lines, 5.0)
    await asyncio.sleep(0.3)
    starts = f.rows("start")
    check("crash at start: three spawns, then one backoff line", len(starts) == 3 and len(w.lines) == 1
          and w.lines[0]["ev"] == "llm_backoff" and w.lines[0]["fails"] == 3 and w.lines[0]["last"] == "exit 3", w.lines)
    r = await w.ask("turn on dark mode", data, 3.0)
    r2 = await w.ask("turn on dark mode", data, 3.0)
    check("during the backoff: rules only at once (why backoff), nothing spawned, logged once",
          r["why"] == r2["why"] == "backoff" and r["ms"] < 50 and len(f.rows("start")) == 3 and len(w.lines) == 1, (r, r2))
    f.set("ok")
    await until(lambda: w.spare is not None and w.spare.alive(), 4.0)
    await spare_ready(w, f, 4)
    r = await w.ask("turn on dark mode", data, 3.0)
    check("after the backoff a new spare starts and answers", r["why"] is None and len(w.lines) == 1, r)
    await w.close()
    w = llm.WarmClaude("/nonexistent/claude", log=(lines := []).append, backoff_s=60.0, pause_file=None,
                       config_dir=Path(td) / "missing-cfg")
    w.start()
    await until(lambda: lines, 3.0)
    r = await w.ask("x", None, 3.0)
    check("a missing binary: three failed spawns, one backoff line, asks answered by the rules",
          len(lines) == 1 and lines[0]["last"] == "spawn FileNotFoundError" and r["why"] == "backoff", (lines, r))
    await w.close()

    # a spare that ends by itself while idle: a young or failed one counts, a clean exit after long idle does not
    f = Fake(td, "idle_exit")
    w = warm(f)
    w.start()
    await spare_ready(w, f, 1)
    w.spare.proc.stdin.close()                    # the fake exits 0 at once: young, so it counts
    await spare_ready(w, f, 2)
    young = w.fails
    w.spare.t0 -= 60                              # as if it had idled a minute
    w.spare.proc.stdin.close()
    await spare_ready(w, f, 3)
    check("idle exit: a young spare's exit counts as a failure, a clean exit after a long idle only gets replaced",
          young == 1 and w.fails == 1 and not w.lines and w.spare.alive(), {"young": young, "fails": w.fails})
    await w.close()

    # pause file
    f = Fake(td, "pause")
    pause = Path(td) / "PAUSE_CLAUDE_BG"
    w = warm(f, pause_file=pause)
    w.start()
    await spare_ready(w, f, 1)
    pause.write_text("")
    r = await w.ask("turn on dark mode", data, 3.0)
    check("pause file present: why paused at once, nothing sent", r["why"] == "paused" and r["ms"] < 50 and not f.rows("msg"), r)
    pause.unlink()
    r = await w.ask("turn on dark mode", data, 3.0)
    check("pause file gone: Opus again", r["why"] is None and len(f.rows("msg")) == 1, r)
    await w.close()

    # cold path
    f = Fake(td, "cold")
    w = warm(f)
    r = await w.ask("turn on dark mode", data, 3.0)
    st, ms = f.rows("start"), f.rows("msg")
    check("cold path: no spare alive -> start one and use it inside the same timeout",
          r["why"] is None and len(st) >= 1 and ms and ms[0]["pid"] == st[0]["pid"], {"r": r})
    await w.close()

    # recycled by age
    f = Fake(td, "age")
    w = warm(f, max_age_s=1.0)
    w.start()
    await spare_ready(w, f, 1)
    pid1 = w.spare.proc.pid
    ok = await until(lambda: w.spare is not None and w.spare.proc.pid != pid1 and gone(pid1), 4.0)
    check("a spare older than max_age_s is replaced (30 min in the service, 1 s here)", ok and not f.rows("msg"))
    await w.close()

    # a second ask while the first runs
    f = Fake(td, "two")
    f.set("ok 0.6")
    w = warm(f)
    w.start()
    await spare_ready(w, f, 1)
    r1, r2 = await asyncio.gather(w.ask("turn on dark mode", data, 4.0), w.ask("switch to light mode", data, 4.0))
    ms = f.rows("msg")
    check("a second ask while the first runs: each gets its own process, both answered, no mix-up",
          r1["why"] is None and r2["why"] is None and llm.to_intent(r1["obj"])["value"] == "dark"
          and llm.to_intent(r2["obj"])["value"] == "light" and len(ms) == 2 and ms[0]["pid"] != ms[1]["pid"], (r1, r2))
    await w.close()

    # a spare that writes before it is asked (another agent spoke to it, the review's ghost turn): retired unused
    once = Path(td) / "ghost.once"
    f = Fake(td, "ghost", FAKE_CLAUDE_GHOST_FILE=str(once), FAKE_CLAUDE_GHOST_S="0.3")
    once.write_text("")
    w = warm(f)
    w.start()
    ok = await until(lambda: f.rows("ghost"), 6.0)
    pid1 = f.rows("ghost")[0]["pid"] if ok else -1
    ok = ok and await until(lambda: gone(pid1) and w.spare is not None and w.spare.alive() and w.spare.proc.pid != pid1, 6.0)
    r = await w.ask("Hey Jarvis, turn on dark mode", data, 3.0)
    ms = f.rows("msg")
    check("idle output: the spare that wrote a turn nobody asked for is retired unused and replaced, logged once "
          "(llm_idle_output, no content); the ask gets its own answer from the new spare, never 'buy eggs'",
          ok and r["why"] is None and llm.to_intent(r["obj"]) == {"intent": "theme", "value": "dark"}
          and w.lines == [{"ev": "llm_idle_output"}] and w.counts.get("idle_output") == 1 and w.fails == 0
          and len(ms) == 1 and ms[0]["pid"] != pid1, {"r": r, "lines": w.lines, "counts": w.counts, "ok": ok})
    await w.close()

    # a CLI that always writes first (a protocol change): three in a row mean the backoff, never a respawn loop
    f = Fake(td, "chatty", FAKE_CLAUDE_GHOST_ALWAYS="1", FAKE_CLAUDE_GHOST_S="0.1")
    w = warm(f, backoff_s=60.0)
    w.start()
    await until(lambda: any(x.get("ev") == "llm_backoff" for x in w.lines), 8.0)
    await asyncio.sleep(1.0)
    n = len(f.rows("start"))
    r = await w.ask("turn on dark mode", data, 3.0)
    check("a CLI that always writes first: three spares retired unused, then one backoff line (last: idle output), "
          "no respawn loop; asks answered by the rules",
          n == 3 and [x["ev"] for x in w.lines] == ["llm_idle_output"] * 3 + ["llm_backoff"]
          and w.lines[-1]["last"] == "idle output" and r["why"] == "backoff" and len(f.rows("start")) == 3
          and not f.rows("msg"), {"starts": n, "lines": w.lines, "r": r})
    await w.close()

    # the child environment, cwd and its own config dir
    f = Fake(td, "env", ANTHROPIC_API_KEY="sk-test-not-a-real-key")
    f.cfg.mkdir(mode=0o755)
    os.chmod(f.cfg, 0o755)                        # an existing, too open folder is tightened
    w = warm(f)
    r = await w.ask("turn on dark mode", data, 3.0)
    st = f.rows("start")
    mode = f.cfg.stat().st_mode & 0o777
    check("child env: ANTHROPIC_API_KEY removed, CLAUDE_CONFIG_DIR its own folder (mode 700), cwd /tmp, the expected flags",
          st and st[0]["api_key"] is False and st[0]["config_dir"] == str(f.cfg) and mode == 0o700 and st[0]["cwd"] == "/tmp"
          and st[0]["problems"] == [] and r["why"] is None, {"start": st[:1], "mode": oct(mode)})
    await w.close()
    d = llm.WarmClaude(FAKE, env={}, pause_file=None)
    home_claude = Path.home() / ".claude"
    check("default config dir: ~/.local/state/tablet-voice/claude, not ~/.claude or below it (no spawn here)",
          d.env["CLAUDE_CONFIG_DIR"] == str(llm.CONFIG_DIR) == str(Path.home() / ".local/state/tablet-voice/claude")
          and home_claude not in llm.CONFIG_DIR.parents and llm.CONFIG_DIR != home_claude, d.env.get("CLAUDE_CONFIG_DIR"))

    # shutdown leaves no child, a SIGTERM-proof one included
    f = Fake(td, "hang")
    f.set("hang")
    w = warm(f)
    w.start()
    await spare_ready(w, f, 1)
    r = await w.ask("turn on dark mode", data, 0.5)
    await spare_ready(w, f, 2)
    await asyncio.sleep(0.3)
    pids = f.pids()
    t0 = time.monotonic()
    await w.close()
    el = time.monotonic() - t0
    check("shutdown: every child reaped (two that ignore stdin EOF and SIGTERM get SIGKILL after 2 s)",
          r["why"] == "timeout" and len(pids) == 2 and all(gone(p) for p in pids) and not w.procs and w.spare is None
          and 1.8 <= el <= 3.5, {"pids": pids, "close_s": round(el, 2)})
    r = await w.ask("turn on dark mode", data, 1.0)
    check("after shutdown an ask answers off at once", r["why"] == "off")
    f = Fake(td, "idle")
    w = warm(f)
    w.start()
    await spare_ready(w, f, 1)
    pid = w.spare.proc.pid
    await w.close()
    check("shutdown with an idle spare: killed and reaped", gone(pid) and not w.procs)


# ------------------------------------------------------------------ part 3: server.py with the fake

async def part3(out):
    import harness as H
    from wsprobe import first, load_wav, speech_end_s, stream_session
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    td = tempfile.mkdtemp(prefix="tvllm-", dir=str(out))
    clips = {}
    for k, (text, voice) in {"add": ("add buy milk to my personal list", "rms"),
                             "howmany": ("how many things are on my list", "slt"),
                             "dark": ("turn on dark mode", "slt"), "false_add": ("add buy milk to my personal list", "slt"),
                             "hj_howmany": ("hey jarvis, how many things are on my list", "slt"),
                             "ph_jarvis": ("hey jarvis", "slt"), "next": ("what is next", "slt")}.items():
        H.flite(text, voice, Path(td) / f"{k}.wav")
        clips[k] = load_wav(str(Path(td) / f"{k}.wav"))
    f = Fake(td, "srv", FAKE_CLAUDE_SLOW_S="10")
    pause = Path(td) / "PAUSE_CLAUDE_BG"
    env = {"VOICE_LLM": "claude", "VOICE_LLM_BIN": str(FAKE), "VOICE_LLM_PAUSE_FILE": str(pause),
           "VOICE_LLM_CONFIG_DIR": str(f.cfg), "VOICE_LLM_TIMEOUT_MS": "1500", "FAKE_CLAUDE_LOG": str(f.log),
           "FAKE_CLAUDE_MODE_FILE": str(f.modef), "FAKE_CLAUDE_SLOW_S": "10"}
    dash = H.start_dash(out, limit_s=900)
    try:
        p = H.start_voice(out, "L-claude", env, limit_s=600)
        try:
            await until(lambda: len(f.rows("start")) >= 1, 10)
            h = H.get_json(H.HTTP + "/health")
            check("L1 /health: llm status with a live spare; cfg llm claude, 1500 ms",
                  (h.get("llm") or {}).get("spare") is True and h["cfg"]["llm"] == "claude" and h["cfg"]["llm_timeout_ms"] == 1500,
                  {"llm": h.get("llm"), "cfg": h.get("cfg")})
            st = f.rows("start")
            start = [r for r in H.read_log(p.log_dir) if r.get("ev") == "start"]
            check("L1b the child runs with VOICE_LLM_CONFIG_DIR as its CLAUDE_CONFIG_DIR (mode 700, never ~/.claude); "
                  "the start line names it",
                  st and all(x["config_dir"] == str(f.cfg) for x in st) and (f.cfg.stat().st_mode & 0o777) == 0o700
                  and start and start[-1]["cfg"].get("llm_config_dir") == str(f.cfg),
                  {"config_dirs": sorted({x["config_dir"] for x in st}), "start_cfg": start[-1]["cfg"].get("llm_config_dir") if start else None})

            def sess_rows(sid):
                time.sleep(0.4)
                return [r for r in H.read_log(p.log_dir) if r.get("ev") == "session" and r.get("sid") == sid]

            async def ptt(key, client="l"):
                n0 = len(f.rows("msg"))
                r = await stream_session(H.VOICE_URL, clips[key], by="ptt", client=client)
                _, res = first(r["msgs"], "result")
                rows = sess_rows(r["sid"])
                return r, res, (rows[-1] if rows else {}), f.rows("msg")[n0:]

            r, res, row, new = await ptt("add")
            check("L2 PTT 'add buy milk ...': the Opus intent runs; the log has llm_used, llm_ms and the rules intent beside it",
                  res and res["intent"] == {"name": "task.add", "title": "buy milk", "list": "personal", "due": None}
                  and res["say"] == "Would add buy milk to Personal." and row.get("llm_used") is True and row.get("llm_fallback") is None
                  and isinstance(row.get("llm_ms"), int) and (row.get("rules_intent") or {}).get("name") == "task.add"
                  and (row.get("llm_intent") or {}).get("name") == "task.add" and len(new) == 1
                  and isinstance(res.get("timing_ms", {}).get("llm"), int),
                  {"heard": res and res.get("heard"), "intent": res and res.get("intent"), "row": {k: row.get(k) for k in
                   ("llm_used", "llm_fallback", "llm_ms", "rules_intent", "llm_intent")}})
            c = new[0]["content"] if new else ""
            check("L3 the prefetched GET /api/data reached Opus (fixture events and tasks in the message)",
                  "Mum's birthday" in c and "Buy milk powder for Ema" in c and "Transcript: " in c, c[-160:])
            data = H.get_json(H.DASH + "/api/data")
            want = f"I see {len(data['events'])} events and {sum(len(v) for v in data['tasks'].values())} open tasks."
            n_calls = len(H.get_json(H.DASH + "/calls"))
            r, res, row, new = await ptt("howmany")
            calls = H.get_json(H.DASH + "/calls")[n_calls:]
            check("L4 PTT question the rules miss: Opus answer from the data, spoken, logged by length only, no dashboard write",
                  res and res["intent"]["name"] == "answer" and res["say"] == want and res["card"] == want and res["ok"] is True
                  and row.get("say") is None and row.get("say_len") == len(want) and row.get("intent") == {"name": "answer", "say_len": len(want)}
                  and (row.get("rules_intent") or {}).get("name") is None and all(x["method"] == "GET" for x in calls)
                  and want not in json.dumps(row),
                  {"heard": res and res.get("heard"), "say": res and res.get("say"), "want": want, "row_intent": row.get("intent")})
            wake_at = round(speech_end_s(clips["ph_jarvis"]) + 0.12, 3)
            n0 = len(f.rows("msg"))
            rw = await stream_session(H.VOICE_URL, clips["hj_howmany"], by="wake", wake_at=wake_at, client="l")
            _, res = first(rw["msgs"], "result")
            _, rej = first(rw["msgs"], "reject")
            wt = ((res or {}).get("check") or {}).get("wake_text")
            if wt:
                check("L5 wake 'hey jarvis, how many ...' (name heard): the answer runs", res["intent"]["name"] == "answer" and res["say"] == want, res)
            else:
                check("L5 wake 'hey jarvis, how many ...' with the name lost by Whisper: answer refused silently",
                      (rej and rej.get("why") == "wake_check") or (res and not res.get("say")), {"res": res, "rej": rej})
            n0 = len(f.rows("msg"))
            rf = await stream_session(H.VOICE_URL, clips["false_add"], by="wake", wake_at=0.9, client="l")
            _, rej = first(rf["msgs"], "reject")
            row = (sess_rows(rf["sid"]) or [{}])[-1]
            if row.get("oww") is not None and row["oww"] < 0.5:
                check("L6 a wake with no name and a low openWakeWord score: Opus skipped, silent reject, words not kept",
                      rej and rej.get("why") == "wake_check" and row.get("llm_fallback") == "skip" and len(f.rows("msg")) == n0
                      and row.get("transcript") == "not_kept" and row.get("rules_intent") == {"name": "task.add"},
                      {k: row.get(k) for k in ("oww", "llm_fallback", "rules_intent", "transcript")})
            else:
                check("L6 (openWakeWord scored this clip high, so Opus was asked; the write still needs the name)",
                      not (first(rf["msgs"], "result")[1] or {}).get("say"), row.get("oww"))
            f.set("slow")
            await asyncio.sleep(0.2)
            r, res, row, new = await ptt("dark")
            t_ep, _ = first(r["msgs"], "endpoint")
            t_res, _ = first(r["msgs"], "result")
            check("L7 Opus slower than VOICE_LLM_TIMEOUT_MS (1.5 s): the rules answer, llm_fallback timeout",
                  res and res["intent"] == {"name": "theme", "value": "dark"} and {"what": "theme", "value": "dark"} in res["do"]
                  and row.get("llm_fallback") == "timeout" and row.get("llm_used") is False and 1400 <= (row.get("llm_ms") or 0) <= 1900
                  and t_res - t_ep >= 1.5, {"llm_ms": row.get("llm_ms"), "endpoint_to_result_s": round(t_res - t_ep, 2) if t_res and t_ep else None})
            f.set("ok")
            await asyncio.sleep(3.0)
            pause.write_text("")
            r, res, row, new = await ptt("dark")
            check("L8 pause file present: the rules answer at once, llm_fallback paused, nothing sent to Opus",
                  res and res["intent"]["name"] == "theme" and row.get("llm_fallback") == "paused" and not new, row.get("llm_fallback"))
            pause.unlink()
            f.set("error")
            r, res, row, new = await ptt("dark")
            check("L9 an error result: the rules answer, llm_fallback error", res and res["intent"]["name"] == "theme"
                  and row.get("llm_fallback") == "error" and len(new) == 1, row.get("llm_fallback"))
            f.set("ok")
            await asyncio.sleep(1.0)
            jl = [json.loads(x) for x in Path(p.log_path).read_text().splitlines() if x.startswith('{"ts"')]
            js = [x for x in jl if x.get("ev") == "session" and "llm_fallback" in x]
            raw = Path(p.log_path).read_text()
            check("L10 journal (stdout): rules_intent and llm_intent are names, no transcript, title or answer text",
                  js and all(isinstance(x.get("llm_intent"), (str, type(None))) and isinstance(x.get("rules_intent"), (str, type(None)))
                             for x in js) and "buy milk" not in raw and want not in raw and "Mum's birthday" not in raw,
                  [{k: x.get(k) for k in ("llm_intent", "rules_intent", "llm_fallback")} for x in js][:6])
            h = H.get_json(H.HTTP + "/health")
            cnt = (h.get("llm") or {}).get("counts") or {}
            check("L11 /health counts the outcomes", cnt.get("ok", 0) >= 2 and cnt.get("timeout") == 1 and cnt.get("paused") == 1
                  and cnt.get("error") == 1, cnt)
            rs = subprocess.run([H.PY, "selftest.py", "--url", H.VOICE_URL], capture_output=True, text=True, timeout=400,
                                cwd=H.ROOT)
            (out / "selftest-L.txt").write_text(rs.stdout + rs.stderr)
            check("L14 selftest.py against the Opus path (fake claude): 9/9, the hello gives llm claude and a 3.5 s answer bound",
                  rs.returncode == 0 and "PASS 9/9" in rs.stdout and "llm claude, answer bound 3.5 s" in rs.stdout,
                  (rs.stdout.strip().splitlines() or [""])[-1])
        finally:
            rc = p.stop()
        await asyncio.sleep(0.5)
        pids = f.pids()
        check("L12 server stops cleanly; no claude child left", rc == 0 and pids and all(gone(x) for x in pids),
              {"rc": rc, "alive": [x for x in pids if not gone(x)]})
        f2 = Fake(td, "off")
        p = H.start_voice(out, "L-off", {"VOICE_LLM": "off", "VOICE_LLM_BIN": str(FAKE), "FAKE_CLAUDE_LOG": str(f2.log)}, limit_s=300)
        try:
            r = await stream_session(H.VOICE_URL, clips["dark"], by="ptt", client="off")
            _, res = first(r["msgs"], "result")
            time.sleep(0.4)
            row = ([x for x in H.read_log(p.log_dir) if x.get("ev") == "session" and x.get("sid") == r["sid"]] or [{}])[-1]
            h = H.get_json(H.HTTP + "/health")
            check("L13 VOICE_LLM=off: the rules, llm_fallback off, nothing spawned, /health llm null",
                  res and res["intent"]["name"] == "theme" and row.get("llm_fallback") == "off" and not f2.rows() and h.get("llm") is None,
                  {"fallback": row.get("llm_fallback"), "fake_rows": len(f2.rows())})
        finally:
            p.stop()
        # a hung dashboard with Opus on: test_server.py H18 and H19 with the service's 3.5 s timeout and a fake that
        # answers in 1.8 s (the real warm p50). The review measured 5.77 s and 3.54 s with the old 1 s data wait.
        f3 = Fake(td, "hung")
        f3.set("ok 1.8")
        p = H.start_voice(out, "L-hung", {"VOICE_LLM": "claude", "VOICE_LLM_BIN": str(FAKE), "VOICE_LLM_PAUSE_FILE": str(pause),
                                          "VOICE_LLM_CONFIG_DIR": str(f3.cfg), "VOICE_LLM_TIMEOUT_MS": "3500",
                                          "FAKE_CLAUDE_LOG": str(f3.log), "FAKE_CLAUDE_MODE_FILE": str(f3.modef)}, limit_s=300)
        try:
            await until(lambda: len(f3.rows("start")) >= 1, 10)
            await asyncio.sleep(0.5)
            dash_control(get_mode="hang")
            try:
                n0 = len(f3.rows("msg"))
                r = await stream_session(H.VOICE_URL, clips["next"], by="ptt", client="hung", tail_s=20.0)
                t_ep, _ = first(r["msgs"], "endpoint")
                t_res, res = first(r["msgs"], "result")
                new = f3.rows("msg")[n0:]
                await asyncio.sleep(0.4)
                rows = H.read_log(p.log_dir)
                ep = [x for x in rows if x.get("ev") == "endpoint" and x.get("sid") == r["sid"]]
                ss = [x for x in rows if x.get("ev") == "session" and x.get("sid") == r["sid"]]
                ask_gap = (round(new[0]["t"] - server.dt.datetime.fromisoformat(ep[-1]["ts"]).timestamp()
                                 - ss[-1]["stt_ms"] / 1000, 3) if ep and ss and new else None)
                check("L15 (H18 with Opus) hung dashboard, push-to-talk 'what is next': 'The dashboard isn't answering.' "
                      "within the 5 s read budget from the wake (<= 5.6 s); Opus was asked without the data as STT ended "
                      "(the old code waited 1 s first)",
                      res and res["say"] == "The dashboard isn't answering." and t_res is not None and t_res <= 5.6
                      and res["intent"]["name"] == "next.event" and len(new) == 1
                      and "Calendar and tasks: not available right now." in new[0]["content"]
                      and ask_gap is not None and ask_gap < 0.4,
                      {"endpoint_s": t_ep, "result_s": t_res, "timing_ms": (res or {}).get("timing_ms"), "msgs": len(new),
                       "ask_after_stt_s": ask_gap})
                await asyncio.sleep(0.5)
                r = await stream_session(H.VOICE_URL, clips["dark"], by="ptt", client="hung", tail_s=8.0)
                t_ep, _ = first(r["msgs"], "endpoint")
                t_res, res = first(r["msgs"], "result")
                tm = (res or {}).get("timing_ms") or {}
                gap = (tm.get("total") or 0) - (tm.get("stt") or 0) - (tm.get("llm") or 0) - (tm.get("action") or 0)
                check("L16 (H19 with Opus) hung dashboard, 'turn on dark mode' needs no dashboard: Opus is asked as STT "
                      "ends (endpoint to result minus STT, Opus and action under 0.4 s) and the theme lands within 3 s",
                      res and res["intent"] == {"name": "theme", "value": "dark"} and isinstance(tm.get("llm"), int)
                      and gap < 400 and t_res - t_ep < 3.0,
                      {"endpoint_to_result_s": round(t_res - t_ep, 2) if t_res and t_ep else None, "timing_ms": tm,
                       "gap_ms": round(gap)})
            finally:
                dash_control(get_mode="ok")
        finally:
            rc = p.stop()
        await asyncio.sleep(0.5)
        pids = f3.pids()
        check("L17 the hung-dashboard server stops cleanly; no claude child left", rc == 0 and pids and all(gone(x) for x in pids),
              {"rc": rc, "alive": [x for x in pids if not gone(x)]})
    finally:
        dash.stop()


def dash_control(**kw):
    import harness as H
    req = urllib.request.Request(H.DASH + "/control", data=json.dumps(kw).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="", help="also run part 3 (server.py on the test ports), writing to this folder")
    a = ap.parse_args()
    t0 = time.time()
    part1_mapping()
    part1_message()
    part1_parse()
    asyncio.run(part1_understand())
    part1_server_bits()
    print(f"--- part 1 done in {time.time() - t0:.1f} s", flush=True)
    with tempfile.TemporaryDirectory(prefix="tvllm-") as td:
        t1 = time.time()
        asyncio.run(part2(td))
        print(f"--- part 2 done in {time.time() - t1:.1f} s", flush=True)
    if a.server:
        t2 = time.time()
        asyncio.run(part3(a.server))
        print(f"--- part 3 done in {time.time() - t2:.1f} s", flush=True)
        (Path(a.server) / "results-llm.json").write_text(json.dumps(RESULTS, indent=1))
    bad = [r for r in RESULTS if not r["ok"]]
    print(f"{len(RESULTS) - len(bad)}/{len(RESULTS)} pass")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
