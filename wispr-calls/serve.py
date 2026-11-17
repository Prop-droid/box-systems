#!/usr/bin/env python3
"""Serve the call follow-up board and keep its tick state on the box.

GET  /       board/index.html (read on each request, so a rebuild shows at once)
GET  /state  {"<item key>": 1, ...} for items marked done
POST /tick   {"k": "<item key>", "done": true|false}
Binds to one address only (the Tailscale address). Never put this behind the funnel.
"""
import datetime
import json
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.environ.get("WISPR_CALLS_DIR", os.path.expanduser("~/.local/share/wispr-calls"))
HOST = os.environ.get("WISPR_BOARD_HOST", "127.0.0.1")
PORT = int(os.environ.get("WISPR_BOARD_PORT", "8099"))
PAGE = os.path.join(BASE, "board", "index.html")
STATE = os.path.join(BASE, "state", "done.json")
KEY = re.compile(r"^[0-9a-f]{12}$")
LOCK = threading.Lock()


def load():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(state):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    json.dump(state, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, STATE)


class H(BaseHTTPRequestHandler):
    server_version = "wispr-board"

    def send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Robots-Tag", "noindex")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            try:
                self.send(200, open(PAGE, "rb").read(), "text/html; charset=utf-8")
            except OSError:
                self.send(503, b"board not built yet", "text/plain")
        elif path == "/state":
            with LOCK:
                body = json.dumps({k: 1 for k in load()}).encode()
            self.send(200, body, "application/json")
        else:
            self.send(404, b"not found", "text/plain")

    def do_POST(self):
        # JSON content type only: a cross-site form post cannot send it.
        if self.path != "/tick" or "application/json" not in (self.headers.get("Content-Type") or ""):
            return self.send(404, b"not found", "text/plain")
        try:
            n = int(self.headers.get("Content-Length") or 0)
            d = json.loads(self.rfile.read(n)) if 0 < n < 1000 else {}
            k, on = d.get("k", ""), bool(d.get("done"))
        except (ValueError, AttributeError):
            k, on = "", False
        if not (isinstance(k, str) and KEY.match(k)):
            return self.send(400, b"bad key", "text/plain")
        with LOCK:
            state = load()
            if on:
                state.setdefault(k, datetime.datetime.now().isoformat(timespec="seconds"))
            else:
                state.pop(k, None)
            save(state)
        self.send(200, b'{"ok":true}', "application/json")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"wispr-board on http://{HOST}:{PORT}/", flush=True)
    try:
        ThreadingHTTPServer((HOST, PORT), H).serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
