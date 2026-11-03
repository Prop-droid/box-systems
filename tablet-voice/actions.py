"""actions.py: Tier 0 intent actions against the dashboard's own endpoints (14d section 7, spec 14 V4).

Reads use GET {VOICE_DASH}/api/data, prefetched at the wake, inside one read budget measured from the wake
(the server passes its deadline; a failed prefetch is retried only when it failed fast, never after a
timeout). Writes POST /api/task/add or /api/task/complete only when the session is not dry, and only if the
page's socket is still open right before the call (otherwise refused "undeliverable"). A write has three
outcomes: answered (the HTTP status decides), not sent (connection refused or a connect failure: "I couldn't
..."), or unknown (the request went out but no answer came back: read timeout, reset, close). An unknown
write may have happened (tablet-dash inserts the task before it waits on its cache lock), so it is never
reported as a failure: "I'm not sure that went through. Check the list." with a refresh, logged post
"unknown". Dry run calls nothing but GET /api/data. Completion is refused unless VOICE_ALLOW_COMPLETE=1 (D6).
"Shopping" is refused until /api/task/add resolves list titles (D7, 14d 7d). Replies stay short (about 200
characters) and free of symbols, for speech. The log-safe summary of each action never carries an endpoint
path unless a POST was answered, and never carries dashboard data (calendar or task titles): those replies
are logged by length only (say_log None).
"""
import datetime as dt
import http.client
import json
import time
import urllib.error
import urllib.request

from intents import best_task

TIMEOUT_S = 5.0          # reads (GET /api/data): also the read budget from the wake (server.py)
WRITE_TIMEOUT_S = 7.0    # writes: STT plus a 7 s write still fit the page's 10 s keep after a dark event
RETRY_MIN_S = 0.5        # a fast-failed prefetch is retried only if this much of the read budget is left
MAX_SAY = 200
LIST_NAMES = {"personal": "Personal", "work": "Work"}
NUM_WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"]
DASH_DOWN = "The dashboard isn't answering."
COMPLETE_OFF = "I can't complete tasks by voice yet."
SHOPPING = "I can only add to personal or work for now."
SORRY = "Sorry, I didn't catch that."
WENT_WRONG = "Sorry, something went wrong."
UNSURE = "I'm not sure that went through. Check the list."


def _http(method, url, body=None, timeout=TIMEOUT_S):
    """Returns (status, parsed JSON body or None). A body that cannot be read or parsed after the status line
    arrived gives None: the server already finished the request (Flask sends headers after the handler)."""
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        status = r.status
        try:
            raw = r.read(4 * 1024 * 1024)
            return status, (json.loads(raw) if raw else None)
        except (OSError, ValueError, http.client.HTTPException):
            return status, None


def outcome(e) -> str:
    """Classify a failed request: "http" (the server answered with an error status), "not_sent" (urllib wraps
    every error raised while connecting and sending in URLError: connection refused, connect timeout, DNS) or
    "unknown" (the request went out and no answer came back: read timeout, reset, remote close)."""
    if isinstance(e, urllib.error.HTTPError):
        return "http"
    if isinstance(e, urllib.error.URLError):
        return "not_sent"
    return "unknown"


def _err(e) -> str:
    """Log-safe error summary: class and HTTP status only, never a URL or payload."""
    if isinstance(e, urllib.error.HTTPError):
        return f"http_{e.code}"
    if isinstance(e, urllib.error.URLError):
        return f"url_{type(e.reason).__name__}"
    return type(e).__name__


def fetch_data(dash: str, timeout: float = TIMEOUT_S) -> dict:
    """GET /api/data. Returns {ok, data, ms, err, fast}; runs in a worker thread. fast = the request never
    reached the server and failed within a second (connection refused, e.g. tablet-dash restarting): the only
    failure worth one retry inside the read budget."""
    t0 = time.perf_counter()
    try:
        status, obj = _http("GET", dash + "/api/data", timeout=timeout)
        ok = status == 200 and isinstance(obj, dict)
        return {"ok": ok, "data": obj if ok else None, "ms": round((time.perf_counter() - t0) * 1000, 1),
                "err": None if ok else f"status_{status}", "fast": False}
    except Exception as e:  # noqa: BLE001  (any failure = dashboard down for this turn)
        secs = time.perf_counter() - t0
        return {"ok": False, "data": None, "ms": round(secs * 1000, 1), "err": _err(e),
                "fast": outcome(e) == "not_sent" and secs < 1.0}


def _clean(s, n=80) -> str:
    s = " ".join(str(s or "").split())
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0]
    return cut if cut else s[:n]


def _trim(s: str) -> str:
    if len(s) <= MAX_SAY:
        return s
    cut = s[:MAX_SAY - 1].rsplit(" ", 1)[0].rstrip(",;:. ")
    return cut + "."


def _parse(s):
    try:
        t = dt.datetime.fromisoformat(str(s))
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo else t.astimezone()


def _day(data: dict, offset: int) -> list:
    """Events of today (0) or tomorrow (1), in the dashboard's order: by `delta`, else by the day's label."""
    label = {0: "Today", 1: "Tomorrow"}[offset]
    key = next((d.get("daykey") for d in (data.get("days") or []) if isinstance(d, dict) and d.get("daylabel") == label), None)
    out = []
    for e in data.get("events") or []:
        if not isinstance(e, dict):
            continue
        if ("delta" in e and e.get("delta") == offset) or ("delta" not in e and key and e.get("daykey") == key):
            out.append(e)
    return out


def next_event(data: dict, now=None) -> str:
    """The page's "next" chip rule (dashboard.html:350-357): first event today that is not all-day and starts
    after now; else the first event of tomorrow."""
    now = now or dt.datetime.now().astimezone()
    for e in _day(data, 0):
        if e.get("time") != "all-day":
            t = _parse(e.get("sort"))
            if t is not None and t > now:
                return f"Next at {e.get('time')}: {_clean(e.get('title'))}."
    tom = _day(data, 1)
    timed = [e for e in tom if e.get("time") != "all-day"]
    if timed:
        return f"Nothing else today. Tomorrow starts at {timed[0].get('time')} with {_clean(timed[0].get('title'))}."
    if tom:
        return f"Nothing else today. Tomorrow: all day, {_clean(tom[0].get('title'))}."
    return "Nothing else today or tomorrow."


def schedule_tomorrow(data: dict) -> str:
    """Events of tomorrow, all-day first, at most 5, plus the number of tasks due tomorrow."""
    tom = _day(data, 1)
    items = ([f"all day, {_clean(e.get('title'), 50)}" for e in tom if e.get("time") == "all-day"] +
             [f"{e.get('time')}, {_clean(e.get('title'), 50)}" for e in tom if e.get("time") != "all-day"])
    n = len(((data.get("tasks") or {}).get("tomorrow")) or [])
    tail = ""
    if n:
        tail = f" {NUM_WORDS[n] if n < len(NUM_WORDS) else n} task{'s' if n != 1 else ''} due."
    if not items:
        return ("Nothing on the calendar tomorrow." + tail).strip()
    budget = MAX_SAY - len("Tomorrow: ") - len(tail) - len(" And 9 more.")
    shown = []
    for it in items[:5]:
        if len(". ".join(shown + [it])) + 1 > budget:
            break
        shown.append(it)
    if not shown:
        shown = [items[0][:budget - 1]]
    s = "Tomorrow: " + ". ".join(shown) + "."
    if len(items) > len(shown):
        s += f" And {len(items) - len(shown)} more."
    return s + tail


def _data(data_res, dash, read_deadline=None):
    """The dashboard data for a read or a completion, inside the read budget (read_deadline, monotonic).
    No prefetch result in time, or one that timed out: the budget is spent, no second request. A prefetch that
    failed fast (connection refused) gets one retry with what is left of the budget."""
    if data_res and data_res.get("ok"):
        return data_res["data"]
    if not data_res or not data_res.get("fast"):
        return None
    left = TIMEOUT_S if read_deadline is None else read_deadline - time.monotonic()
    if left < RETRY_MIN_S:
        return None
    again = fetch_data(dash, timeout=min(TIMEOUT_S, left))
    return again["data"] if again["ok"] else None


def _write_failed(kind, path, e, verb):
    """The reply and log record for a write whose request raised (14d 13 plus the unknown outcome)."""
    how = outcome(e)
    if how == "unknown":                  # sent, no answer: it may have been written; never say "couldn't"
        return {"ok": False, "say": UNSURE, "do": [{"what": "refresh"}], "unsure": True,
                "action": {"kind": kind, "post": "unknown", "err": _err(e)}, "say_log": UNSURE}
    if how == "http":
        say = f"I couldn't {verb} that."
        return {"ok": False, "say": say, "action": {"kind": kind, "post": path, "status": e.code}, "say_log": say}
    say = f"I couldn't {verb} that. " + DASH_DOWN
    return {"ok": False, "say": say, "action": {"kind": kind, "post": "not_sent", "err": _err(e)}, "say_log": say}


def _task_add(slots, dry, dash, deliverable, on_write=None):
    title = _clean(slots.get("title"), 120)
    lst = slots.get("list") or "personal"
    due = slots.get("due") if slots.get("due") in ("today", "tomorrow") else None
    if len(title) < 2:
        return {"ok": False, "say": SORRY, "action": {"kind": "task.add", "skipped": "title"}, "say_log": SORRY}
    if lst not in LIST_NAMES:
        return {"ok": False, "say": SHOPPING, "action": {"kind": "task.add", "skipped": "list", "list": lst}, "say_log": SHOPPING}
    where = LIST_NAMES[lst] + (f" for {due}" if due else "")
    if dry:
        say = _trim(f"Would add {title} to {where}.")
        return {"ok": True, "say": say, "action": {"kind": "task.add", "dry": True, "list": lst, "due": due}, "say_log": say}
    if not deliverable():
        return {"ok": False, "say": None, "card": None, "refused": "undeliverable",
                "action": {"kind": "task.add", "written": False}, "say_log": None}
    body = {"title": title[:1].upper() + title[1:], "due": due, "list": lst}
    if on_write:
        on_write()                        # the server's turn budget now knows a write may land
    try:
        status, obj = _http("POST", dash + "/api/task/add", body, timeout=WRITE_TIMEOUT_S)
    except Exception as e:  # noqa: BLE001
        return _write_failed("task.add", "/api/task/add", e, "add")
    if status == 200 and (obj is None or (isinstance(obj, dict) and obj.get("ok"))):
        say = _trim(f"Added {title} to {where}.")
        return {"ok": True, "say": say, "do": [{"what": "refresh"}],
                "action": {"kind": "task.add", "post": "/api/task/add", "status": status, "list": lst, "due": due}, "say_log": say}
    say = "I couldn't add that."
    return {"ok": False, "say": say, "action": {"kind": "task.add", "post": "/api/task/add", "status": status}, "say_log": say}


def _task_complete(slots, dry, dash, data_res, deliverable, allow_complete, read_deadline=None, on_write=None):
    if not allow_complete:
        return {"ok": False, "say": COMPLETE_OFF, "refused": "complete_off",
                "action": {"kind": "task.complete", "enabled": False}, "say_log": COMPLETE_OFF}
    data = _data(data_res, dash, read_deadline)
    if data is None:
        return {"ok": False, "say": DASH_DOWN, "action": {"kind": "task.complete", "data": "down"}, "say_log": DASH_DOWN}
    tasks = [t for b in ("overdue", "today", "tomorrow", "backlog")
             for t in ((data.get("tasks") or {}).get(b) or []) if isinstance(t, dict) and t.get("title")]
    query = _clean(slots.get("query"), 60)
    r = best_task(query, tasks)
    if r["status"] == "none":
        say = _trim(f"I couldn't find a task called {query}.")
        return {"ok": False, "say": say, "action": {"kind": "task.complete", "match": "none", "score": r.get("score")}, "say_log": say}
    if r["status"] == "ambiguous":
        a, b = (r["options"] + ["", ""])[:2]
        say = _trim(f"Which one: {_clean(a, 60)}, or {_clean(b, 60)}?")
        return {"ok": False, "say": say, "action": {"kind": "task.complete", "match": "ambiguous"}, "say_log": None}
    task = r["task"]
    title = _clean(task.get("title"), 80)
    if dry:
        say = _trim(f"Would complete {title}.")
        return {"ok": True, "say": say, "action": {"kind": "task.complete", "dry": True, "score": r.get("score")}, "say_log": None}
    if not deliverable():
        return {"ok": False, "say": None, "card": None, "refused": "undeliverable",
                "action": {"kind": "task.complete", "written": False}, "say_log": None}
    if on_write:
        on_write()
    try:
        status, obj = _http("POST", dash + "/api/task/complete", {"tl": task.get("tl"), "id": task.get("id")},
                            timeout=WRITE_TIMEOUT_S)
    except Exception as e:  # noqa: BLE001
        return _write_failed("task.complete", "/api/task/complete", e, "complete")
    if status == 200 and (obj is None or (isinstance(obj, dict) and obj.get("ok"))):
        say = _trim(f"Done: {title}.")
        return {"ok": True, "say": say, "do": [{"what": "refresh"}],
                "action": {"kind": "task.complete", "post": "/api/task/complete", "status": status}, "say_log": None}
    say = "I couldn't complete that."
    return {"ok": False, "say": say, "action": {"kind": "task.complete", "post": "/api/task/complete", "status": status}, "say_log": say}


def run(name, slots, *, dry, dash, data_res, deliverable, allow_complete, read_deadline=None, on_write=None) -> dict:
    """Run one matched intent. Returns {ok, say, card, do, refused, action, say_log, say_len}; runs in a worker
    thread. read_deadline (monotonic) is the end of the read budget that started at the wake; on_write() is
    called right before a POST goes out."""
    t0 = time.perf_counter()
    try:
        if name == "cancel":
            out = {"ok": True, "say": None, "card": None, "action": {"kind": "cancel"}, "say_log": None}
        elif name == "theme":
            v = slots.get("value") if slots.get("value") in ("dark", "light", "auto") else "dark"
            say = {"dark": "Dark mode on.", "light": "Light mode on.", "auto": "Auto theme on."}[v]
            out = {"ok": True, "say": say, "do": [{"what": "theme", "value": v}], "action": {"kind": "theme", "value": v}, "say_log": say}
        elif name == "task.add":
            out = _task_add(slots, dry, dash, deliverable, on_write)
        elif name == "task.complete":
            out = _task_complete(slots, dry, dash, data_res, deliverable, allow_complete, read_deadline, on_write)
        elif name in ("next.event", "schedule.tomorrow"):
            data = _data(data_res, dash, read_deadline)
            if data is None:
                out = {"ok": False, "say": DASH_DOWN, "action": {"kind": name, "data": "down"}, "say_log": DASH_DOWN}
            else:
                say = _trim(next_event(data) if name == "next.event" else schedule_tomorrow(data))
                out = {"ok": True, "say": say, "action": {"kind": name}, "say_log": None}
        else:
            out = {"ok": False, "say": SORRY, "action": {"kind": str(name)}, "say_log": SORRY}
    except Exception as e:  # noqa: BLE001
        out = {"ok": False, "say": WENT_WRONG, "action": {"kind": str(name), "err": _err(e)}, "say_log": WENT_WRONG}
    out.setdefault("do", [])
    out.setdefault("refused", None)
    out.setdefault("card", out.get("say"))
    out["say_len"] = len(out["say"]) if out.get("say") else 0
    out["action"]["ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return out
