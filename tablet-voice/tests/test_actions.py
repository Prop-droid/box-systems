#!/usr/bin/env python3
"""tests/test_actions.py: deterministic unit tests for the reply logic and the V4 decision table.

No network, no models, no server: actions._http is replaced by a stub that records calls, and server.decide()
is checked against every row of the decision table (spec 14 V4 with section 0 item 11). The 15a Fix round adds
the write outcomes (answered, not sent, unknown), the read budget, the journal redaction, strict JSON lines,
the log line budget and the streaming ledger replay.
Run: .venv/bin/python tests/test_actions.py   (exit 0 = all pass)
"""
import datetime as dt
import http.client
import json
import os
import sys
import tempfile
import time
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("VOICE_STAGE", "skeleton")
import actions  # noqa: E402
import server  # noqa: E402

OK = []


def check(name, cond, detail=""):
    OK.append(bool(cond))
    print(f"{'PASS' if cond else 'FAIL'} {name}{': ' + str(detail) if detail else ''}")


NOW = dt.datetime(2026, 11, 2, 15, 0).astimezone()


def ev(day_off, hhmm, title):
    d = (NOW + dt.timedelta(days=day_off)).date()
    if hhmm == "all-day":
        return {"time": "all-day", "title": title, "sort": d.isoformat(), "delta": day_off}
    h, m = map(int, hhmm.split(":"))
    return {"time": hhmm, "title": title, "sort": dt.datetime.combine(d, dt.time(h, m)).astimezone().isoformat(), "delta": day_off}


DATA = {"days": [{"daykey": "d0", "daylabel": "Today"}, {"daykey": "d1", "daylabel": "Tomorrow"}],
        "events": [ev(0, "all-day", "Bin day"), ev(0, "09:00", "Standup"), ev(0, "16:30", "Dentist"),
                   ev(1, "all-day", "Mum's birthday"), ev(1, "09:00", "Standup"), ev(1, "14:30", "Dentist")],
        "tasks": {"overdue": [], "today": [{"title": "Buy milk", "id": "1", "tl": "L1"}],
                  "tomorrow": [{"title": "Call the dentist", "id": "2", "tl": "L1"}, {"title": "Renew passport", "id": "3", "tl": "L2"}],
                  "backlog": [{"title": "Buy milk powder for Ema", "id": "4", "tl": "L1"}]}}
RES = {"ok": True, "data": DATA, "ms": 1.0, "err": None}

# replies
check("next.event: first timed event after now", actions.next_event(DATA, NOW) == "Next at 16:30: Dentist.", actions.next_event(DATA, NOW))
late = NOW.replace(hour=20)
check("next.event: nothing left today -> tomorrow's first timed event", actions.next_event(DATA, late) == "Nothing else today. Tomorrow starts at 09:00 with Standup.")
only_allday = {"events": [ev(1, "all-day", "Mum's birthday")]}
check("next.event: only an all-day event tomorrow", actions.next_event(only_allday, late) == "Nothing else today. Tomorrow: all day, Mum's birthday.")
check("next.event: nothing at all", actions.next_event({"events": []}, late) == "Nothing else today or tomorrow.")
check("schedule.tomorrow: 14d's example form", actions.schedule_tomorrow(DATA) == "Tomorrow: all day, Mum's birthday. 09:00, Standup. 14:30, Dentist. Two tasks due.",
      actions.schedule_tomorrow(DATA))
many = {"events": [ev(1, f"{8 + i:02d}:00", f"Meeting number {i} with a rather long descriptive title") for i in range(8)], "tasks": {}}
s = actions.schedule_tomorrow(many)
check("schedule.tomorrow: at most about 200 characters, rest counted", len(s) <= 200 and "more." in s, f"{len(s)}: {s}")
check("schedule.tomorrow: empty day", actions.schedule_tomorrow({"events": [], "tasks": {"tomorrow": [1]}}) == "Nothing on the calendar tomorrow. One task due.")

# runs with a stubbed HTTP layer
CALLS = []


def stub(method, url, body=None, timeout=5):
    CALLS.append((method, url, body))
    return 200, {"ok": True}


actions._http = stub
yes, no = (lambda: True), (lambda: False)
r = actions.run("task.add", {"title": "buy milk", "list": "personal", "due": None}, dry=True, dash="http://d", data_res=None, deliverable=yes, allow_complete=False)
check("task.add dry: 'Would add', no call", r["say"] == "Would add buy milk to Personal." and not CALLS and r["ok"], r["say"])
r = actions.run("task.add", {"title": "call the dentist", "list": "work", "due": "tomorrow"}, dry=False, dash="http://d", data_res=None, deliverable=yes, allow_complete=False)
check("task.add live: POST body capitalised, reply, refresh", r["say"] == "Added call the dentist to Work for tomorrow." and CALLS[-1] ==
      ("POST", "http://d/api/task/add", {"title": "Call the dentist", "due": "tomorrow", "list": "work"}) and r["do"] == [{"what": "refresh"}], CALLS[-1])
n = len(CALLS)
r = actions.run("task.add", {"title": "buy milk", "list": "personal", "due": None}, dry=False, dash="http://d", data_res=None, deliverable=no, allow_complete=False)
check("task.add live, socket gone: refused undeliverable, nothing written", r["refused"] == "undeliverable" and r["say"] is None and len(CALLS) == n)
r = actions.run("task.add", {"title": "eggs", "list": "shopping", "due": None}, dry=False, dash="http://d", data_res=None, deliverable=yes, allow_complete=False)
check("task.add shopping: refused with 14d 7d's line, nothing written", r["say"] == "I can only add to personal or work for now." and len(CALLS) == n)
r = actions.run("task.complete", {"query": "milk"}, dry=False, dash="http://d", data_res=RES, deliverable=yes, allow_complete=False)
check("task.complete with completion off (D6): complete_off, nothing written", r["refused"] == "complete_off" and r["say"] == "I can't complete tasks by voice yet." and len(CALLS) == n)
r = actions.run("task.complete", {"query": "milk"}, dry=False, dash="http://d", data_res=RES, deliverable=yes, allow_complete=True)
check("task.complete ambiguous: 'Which one', nothing written", r["say"] == "Which one: Buy milk, or Buy milk powder for Ema?" and len(CALLS) == n, r["say"])
r = actions.run("task.complete", {"query": "car"}, dry=False, dash="http://d", data_res=RES, deliverable=yes, allow_complete=True)
check("task.complete no match: 'I couldn't find'", r["say"] == "I couldn't find a task called car." and len(CALLS) == n)
r = actions.run("task.complete", {"query": "by milke"}, dry=True, dash="http://d", data_res=RES, deliverable=yes, allow_complete=True)
check("task.complete dry pick: 'Would complete Buy milk.'", r["say"] == "Would complete Buy milk." and len(CALLS) == n)
r = actions.run("task.complete", {"query": "by milke"}, dry=False, dash="http://d", data_res=RES, deliverable=yes, allow_complete=True)
check("task.complete live: POST tl and id, 'Done: Buy milk.'", r["say"] == "Done: Buy milk." and CALLS[-1] == ("POST", "http://d/api/task/complete", {"tl": "L1", "id": "1"}))
check("dashboard replies never log calendar or task titles", r["say_log"] is None)


def raiser(exc):
    def f(*a, **k):
        CALLS.append(("raise", type(exc).__name__))
        raise exc
    return f


REFUSED = urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))
actions._http = raiser(REFUSED)
r = actions.run("next.event", {}, dry=True, dash="http://d", data_res={"ok": False, "data": None, "ms": 1, "err": "x", "fast": False}, deliverable=yes, allow_complete=False)
check("dashboard down on a read: 'The dashboard isn't answering.'", r["say"] == "The dashboard isn't answering." and not r["ok"])
ADD = {"title": "buy milk", "list": "personal", "due": None}
r = actions.run("task.add", ADD, dry=False, dash="http://d", data_res=None, deliverable=yes, allow_complete=False)
check("write not sent (connection refused): 'I couldn't add that. The dashboard isn't answering.', post not_sent",
      r["say"] == "I couldn't add that. The dashboard isn't answering." and r["action"]["post"] == "not_sent"
      and r["action"]["err"] == "url_ConnectionRefusedError" and "http://d" not in str(r["action"]), r["action"])

# 15a Fix round, finding 3: a write that went out but got no answer may have happened
for exc in (TimeoutError("timed out"), http.client.RemoteDisconnected("closed"), ConnectionResetError(104, "reset")):
    actions._http = raiser(exc)
    r = actions.run("task.add", ADD, dry=False, dash="http://d", data_res=None, deliverable=yes, allow_complete=False)
    check(f"write sent, no answer ({type(exc).__name__}): unsure line, refresh, post unknown, never 'couldn't'",
          r["say"] == actions.UNSURE and r["card"] == actions.UNSURE and r["ok"] is False and r["do"] == [{"what": "refresh"}]
          and r["action"]["post"] == "unknown" and "couldn't" not in r["say"] and r.get("unsure") is True, r)
actions._http = raiser(urllib.error.HTTPError("http://d/api/task/add", 500, "err", {}, None))
r = actions.run("task.add", ADD, dry=False, dash="http://d", data_res=None, deliverable=yes, allow_complete=False)
check("write answered with HTTP 500: 'I couldn't add that.', status logged", r["say"] == "I couldn't add that." and r["action"]["status"] == 500, r)
actions._http = lambda *a, **k: (200, None)
r = actions.run("task.add", ADD, dry=False, dash="http://d", data_res=None, deliverable=yes, allow_complete=False)
check("write answered 200 with an unreadable body: added (the handler finished)", r["say"] == "Added buy milk to Personal." and r["ok"], r["say"])
actions._http = raiser(TimeoutError("timed out"))
r = actions.run("task.complete", {"query": "by milke"}, dry=False, dash="http://d", data_res=RES, deliverable=yes, allow_complete=True)
check("completion sent, no answer: the same unsure line", r["say"] == actions.UNSURE and r["action"]["post"] == "unknown", r)
check("write timeout is 7 s, read timeout 5 s", actions.WRITE_TIMEOUT_S == 7.0 and actions.TIMEOUT_S == 5.0)
marks = []
actions._http = lambda *a, **k: (200, {"ok": True})
for kw in ({"dry": True, "deliverable": yes}, {"dry": False, "deliverable": no}):
    actions.run("task.add", ADD, dash="http://d", data_res=None, allow_complete=False, on_write=lambda: marks.append(1), **kw)
actions.run("task.add", {"title": "eggs", "list": "shopping", "due": None}, dry=False, dash="http://d", data_res=None,
            deliverable=yes, allow_complete=False, on_write=lambda: marks.append(1))
n_before = len(marks)
actions.run("task.add", ADD, dry=False, dash="http://d", data_res=None, deliverable=yes, allow_complete=False,
            on_write=lambda: marks.append(1))
check("on_write fires only right before a real POST (not for dry, undeliverable or shopping)", n_before == 0 and len(marks) == 1, marks)
check("outcome(): HTTPError http, URLError not_sent, raw timeout or reset unknown",
      [actions.outcome(e) for e in (urllib.error.HTTPError("u", 404, "x", {}, None), REFUSED,
                                    urllib.error.URLError(TimeoutError()), TimeoutError(), ConnectionResetError(),
                                    http.client.RemoteDisconnected("x"), http.client.BadStatusLine("x"))]
      == ["http", "not_sent", "not_sent", "unknown", "unknown", "unknown", "unknown"])

# finding 5: one read budget from the wake; retry only a fast failure
n = len(CALLS)
actions._http = raiser(REFUSED)
r = actions.run("next.event", {}, dry=True, dash="http://d", data_res=None, deliverable=yes, allow_complete=False,
                read_deadline=time.monotonic() + 4)
check("read, no prefetch result in time: no second request", r["say"] == actions.DASH_DOWN and len(CALLS) == n)
r = actions.run("next.event", {}, dry=True, dash="http://d", data_res={"ok": False, "err": "TimeoutError", "fast": False},
                deliverable=yes, allow_complete=False, read_deadline=time.monotonic() + 4)
check("read, prefetch timed out: no retry (never two sequential timeouts)", r["say"] == actions.DASH_DOWN and len(CALLS) == n)
seen = []


def ok_once(method, url, body=None, timeout=5):
    seen.append(timeout)
    return 200, DATA


actions._http = ok_once
r = actions.run("next.event", {}, dry=True, dash="http://d", data_res={"ok": False, "err": "url_ConnectionRefusedError", "fast": True},
                deliverable=yes, allow_complete=False, read_deadline=time.monotonic() + 2.0)
check("read, prefetch failed fast with budget left: one retry inside the budget", r["ok"] and len(seen) == 1 and seen[0] <= 2.0, seen)
seen.clear()
r = actions.run("next.event", {}, dry=True, dash="http://d", data_res={"ok": False, "err": "url_ConnectionRefusedError", "fast": True},
                deliverable=yes, allow_complete=False, read_deadline=time.monotonic() + 0.2)
check("read, fast failure but the budget is spent: no retry", r["say"] == actions.DASH_DOWN and not seen)
actions._http = raiser(REFUSED)
f = actions.fetch_data("http://d", timeout=1.0)
actions._http = raiser(TimeoutError("timed out"))
g = actions.fetch_data("http://d", timeout=1.0)
check("fetch_data marks connection refused fast and a timeout not fast", f["fast"] is True and g["fast"] is False, (f, g))
r = actions.run("theme", {"value": "auto"}, dry=True, dash="http://d", data_res=None, deliverable=yes, allow_complete=False)
check("theme auto: page do only", r["do"] == [{"what": "theme", "value": "auto"}] and r["say"] == "Auto theme on.")
check("every reply fits about 200 characters", all(len(x) <= 200 for x in (s, actions.schedule_tomorrow(DATA))))

# the decision table (server.decide), D11 default and strict
server.CFG.read_needs_wake_text = False
T = [  # by, intent, wake_text, oww_hi, junk -> kind
    ("ptt", "task.add", False, False, False, "run"), ("ptt", None, False, False, False, "sorry"), ("ptt", None, False, False, True, "sorry"),
    ("wake", "task.add", True, False, False, "run"), ("wake", "task.add", False, True, False, "refuse_wake_text"),
    ("wake", "task.add", False, False, False, "silent_reject"), ("wake", "task.complete", False, True, False, "refuse_wake_text"),
    ("wake", "next.event", False, True, False, "run"), ("wake", "next.event", True, False, False, "run"),
    ("wake", "next.event", False, False, False, "silent_reject"), ("wake", "theme", False, True, False, "run"),
    ("wake", "cancel", False, False, False, "silent_reject"), ("wake", None, True, True, False, "sorry"),
    ("wake", None, False, True, False, "silent_result"), ("wake", None, True, False, False, "silent_result"),
    ("wake", "task.add", True, True, True, "junk"),
]
bad = [(row, server.decide(*row[:5])) for row in T if server.decide(*row[:5]) != row[5]]
check(f"decision table, default reads ({len(T)} rows)", not bad, bad)
server.CFG.read_needs_wake_text = True
T2 = [("wake", "next.event", False, True, False, "silent_reject"), ("wake", "next.event", True, False, False, "run"),
      ("wake", "theme", False, True, False, "silent_reject"), ("wake", "task.add", False, True, False, "refuse_wake_text")]
bad = [(row, server.decide(*row[:5])) for row in T2 if server.decide(*row[:5]) != row[5]]
check(f"decision table, strict reads D11 ({len(T2)} rows)", not bad, bad)
server.CFG.read_needs_wake_text = False

# access helpers
check("allowed_peer: 127.0.0.1 and 192.168.1.89 yes; 127.0.0.2, 192.168.1.6, tailnet no",
      server.allowed_peer("127.0.0.1") and server.allowed_peer("192.168.1.89") and not server.allowed_peer("127.0.0.2")
      and not server.allowed_peer("192.168.1.6") and not server.allowed_peer("100.107.26.69"))
check("peer parsing strips the IPv4-mapped prefix", server._peer(("::ffff:192.168.1.89", 5555, 0, 0)) == "192.168.1.89")

# findings 1 and 10: what reaches the journal
sess = {"ev": "session", "sid": "s1", "by": "wake", "heard": "Hey Jarvis add buy milk to my personal list", "text": "add buy milk to my personal list",
        "intent": {"name": "task.add", "title": "buy milk", "list": "personal", "due": None}, "say": "Would add buy milk to Personal.",
        "wake_text": True, "oww": 0.99, "outcome": "run", "stt_ms": 900, "total_ms": 950, "action_ms": 1.2}
jv = server.journal_view(sess)
check("journal: session line without transcript, slots or reply; heard_len, intent name, outcome, scores, timings kept",
      not {"heard", "text", "say"} & set(jv) and jv["intent"] == "task.add" and jv["heard_len"] == len(sess["heard"])
      and jv["wake_text"] is True and jv["oww"] == 0.99 and jv["outcome"] == "run" and jv["stt_ms"] == 900 and "buy milk" not in json.dumps(jv), jv)
st = {"ev": "stats", "page": {"type": "stats", "samplesPerSec": 16000, "rmsP10": 0.01, "rmsP50": 0.02, "rmsP90": 0.03, "rmsMax": 0.2, "dropped": 0}}
check("journal: stats line without the room loudness profile", not any(k.startswith("rms") for k in server.journal_view(st)["page"])
      and server.journal_view(st)["page"]["samplesPerSec"] == 16000)
check("journal: other lines unchanged", server.journal_view({"ev": "hello", "peer": "x"}) == {"ev": "hello", "peer": "x"})

# finding 9: strict JSON, ASCII lines, finite numbers only
line = server._dumps({"a": float("nan"), "b": float("inf"), "c": "x\u2028y\u2029z\u0085", "d": [float("-inf"), 1.5]})
strict = json.loads(line, parse_constant=server._bad_constant)
check("log lines: NaN and Infinity become null; U+2028, U+2029, U+0085 escaped; ASCII only; one line",
      strict == {"a": None, "b": None, "c": "x\u2028y\u2029z\u0085", "d": [None, 1.5]} and line.isascii() and len(line.splitlines()) == 1, line)
check("page messages: NaN or Infinity tokens and deep nesting are rejected, 1e999 is not a number",
      server._loads('{"a": NaN}') is None and server._loads('{"a": -Infinity}') is None and server._loads("[" * 100000) is None
      and server._num(server._loads('{"a": 1e999}')["a"]) is None and server._num(2.5) == 2.5 and server._num(True) is None)

# finding 4: the line budget
class Sink:
    def __init__(self):
        self.rows = []

    def write(self, ev):
        self.rows.append(ev)


server.LOG = Sink()
g = server.LogGate(burst=5, total=8, window_s=60.0)
a = [g.allow("rejected", "10.0.0.9") for _ in range(300)]
b = [g.allow("rejected", "10.0.0.8") for _ in range(10)]
check("line budget: 5 per peer and window, then held back; the total cap holds across peers",
      sum(a) == 5 and sum(b) == 3, (sum(a), sum(b)))
g.t0 -= 61
g.roll()
sup = [r for r in server.LOG.rows if r.get("ev") == "suppressed"]
check("line budget: one suppressed line per window with the count", len(sup) == 1 and sup[0]["n"] == 302 and sup[0]["top"][0]["peer"] == "10.0.0.9", sup)
check("line budget: a new window lets lines through again", g.allow("rejected", "10.0.0.9") is True)

# findings 4 and 9: the ledger replay streams the file and splits on newline only
with tempfile.TemporaryDirectory() as td:
    pth = Path(td) / "sessions-x.jsonl"
    rows = [{"ev": "state", "peer": "192.168.1.89", "mic_closed_s": 2.0, "reason": "x\u2028y"},
            {"ev": "state", "peer": "192.168.1.89", "mic_closed_s": 1.0, "lit_rise": True},
            {"ev": "session", "peer": "192.168.1.89", "by": "ptt", "outcome": "run", "stt_ms": 800},
            {"ev": "rejected", "why": "peer", "peer": "10.0.0.9", "path": "/health"}]
    with open(pth, "w", encoding="utf-8") as fh:
        for rr in rows:
            fh.write(json.dumps(rr, ensure_ascii=False) + "\n")    # the old writer: a raw U+2028 inside a line
        fh.write("not json\n")
    led = server.Ledger()
    n_s = led.replay(pth)
    check("replay: a raw U+2028 inside a line no longer splits it (3.0 s of mic time, one lit period, one session)",
          led.mic_s == 3.0 and led.lit_periods == 1 and n_s == 1 and led.runs == 1, (led.mic_s, led.lit_periods, n_s))

print(f"{sum(OK)}/{len(OK)} pass")
sys.exit(0 if all(OK) else 1)
