#!/usr/bin/env python3
"""tests/fake_dash.py: stand-in for tablet-dash on a test port, with synthetic data only.

  GET  /api/data            fixture built around the current time (no real calendar or task data)
  POST /api/task/add        recorded, answers {"ok": true}
  POST /api/task/complete   recorded, answers {"ok": true}
  GET  /?cmd=...            fake Fully REST answer {"status": "OK"}; the password value is redacted in the record
  GET  /calls               every recorded call as JSON
  POST /control             fault modes for the next calls (15a Fix round), any subset of
                            {"get_mode": "ok"|"hang", "post_mode": "ok"|"reset"|"http500", "post_delay_s": N}:
                            hang = accept and never answer /api/data; reset = record the write, then close the
                            connection without an answer; post_delay_s = record and answer after N seconds

Usage (always bounded): timeout 600 .venv/bin/python tests/fake_dash.py [--host 127.0.0.2] [--port 18765]
Stops on its own when stdin reaches EOF (the test harness closes it) or when timeout ends it.
"""
import argparse
import datetime as dt
import json
import os
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CALLS = []
LOCK = threading.Lock()
MODE = {"get_mode": "ok", "post_mode": "ok", "post_delay_s": 0.0}


def fixture() -> dict:
    now = dt.datetime.now().astimezone()
    today, tomorrow = now.date(), now.date() + dt.timedelta(days=1)
    days = [{"daykey": (today + dt.timedelta(days=i)).isoformat(),
             "daylabel": "Today" if i == 0 else "Tomorrow" if i == 1 else (today + dt.timedelta(days=i)).strftime("%a %b %d")}
            for i in range(7)]

    def ev(day, hhmm, title, delta):
        if hhmm == "all-day":
            return {"time": "all-day", "title": title, "source": "personal", "sort": day.isoformat(), "delta": delta,
                    "daykey": day.isoformat(), "daylabel": days[delta]["daylabel"]}
        h, m = map(int, hhmm.split(":"))
        t = dt.datetime.combine(day, dt.time(h, m)).astimezone()
        return {"time": hhmm, "title": title, "source": "personal", "sort": t.isoformat(), "delta": delta,
                "daykey": day.isoformat(), "daylabel": days[delta]["daylabel"]}

    events = [ev(today, "all-day", "Bin day", 0)]
    past = now - dt.timedelta(hours=2)
    if past.date() == today:
        events.append(ev(today, past.strftime("%H:%M"), "Morning standup", 0))
    soon = now + dt.timedelta(minutes=90)
    if soon.date() == today:
        events.append(ev(today, soon.strftime("%H:%M"), "Dentist", 0))
    events += [ev(tomorrow, "all-day", "Mum's birthday", 1), ev(tomorrow, "09:00", "Standup", 1),
               ev(tomorrow, "14:30", "Dentist", 1)]
    events.sort(key=lambda e: e["sort"])

    def task(title, i, lst="PERSONAL", due=None):
        t = {"list": lst, "title": title, "id": f"task{i}", "tl": "list-personal" if lst == "PERSONAL" else "list-work"}
        if due:
            t["due"] = due
        return t
    tasks = {"overdue": [], "today": [task("Buy milk", 1, due=today.isoformat())],
             "tomorrow": [task("Call the dentist", 2, due=tomorrow.isoformat()), task("Renew passport", 3, "Work", tomorrow.isoformat())],
             "backlog": [task("Buy milk powder for Ema", 4), task("Tax return 2026", 5, "Work"), task("Book car service", 6)]}
    return {"generated": now.strftime("%H:%M"), "date": now.strftime("%A, %B %d"), "battery": None,
            "days": days, "events": events, "tasks": tasks}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (BrokenPipeError, ConnectionResetError):
            pass       # the client gave up first (timeouts are the point of the fault modes)

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _record(self, method, path, body=None):
        with LOCK:
            CALLS.append({"t": dt.datetime.now().isoformat(timespec="milliseconds"), "method": method, "path": path, "body": body})

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        if u.path == "/api/data":
            self._record("GET", "/api/data")
            if MODE["get_mode"] == "hang":
                time.sleep(30)
                self.close_connection = True
                return None
            return self._send(200, fixture())
        if u.path == "/calls":
            with LOCK:
                return self._send(200, list(CALLS))
        if u.path == "/" and u.query:
            q = dict(urllib.parse.parse_qsl(u.query))
            if "password" in q:
                q["password"] = "<redacted>"
            self._record("GET", "/?cmd", q)
            return self._send(200, {"status": "OK", "statustext": "fake"})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"null")
        except ValueError:
            body = None
        if self.path == "/control":
            with LOCK:
                MODE.update({k: v for k, v in (body or {}).items() if k in MODE})
                return self._send(200, dict(MODE))
        if self.path in ("/api/task/add", "/api/task/complete"):
            if MODE["post_delay_s"]:
                time.sleep(float(MODE["post_delay_s"]))
            self._record("POST", self.path, body)
            if MODE["post_mode"] == "reset":
                self.close_connection = True
                return None
            if MODE["post_mode"] == "http500":
                return self._send(500, {"ok": False})
            return self._send(200, {"ok": True})
        self._send(404, {"ok": False})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.2")
    ap.add_argument("--port", type=int, default=18765)
    a = ap.parse_args()
    srv = ThreadingHTTPServer((a.host, a.port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(json.dumps({"fake_dash": f"http://{a.host}:{a.port}"}), flush=True)
    try:
        while os.read(0, 4096):        # stop when the harness closes stdin
            pass
    except OSError:
        pass
    srv.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
