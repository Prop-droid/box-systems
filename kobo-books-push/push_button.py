#!/usr/bin/env python3
# One-tap manual trigger for kobo-books-push, replacing the hourly timer.
# GET /       -> page with a Push button
# GET /push   -> starts kobo-books-push.service (async), bounces to /status
# GET /status -> live state + last_run.log, auto-refreshes while running
import html
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8091
LOG = Path.home() / "systems/kobo-books-push/last_run.log"

PAGE = """<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">{refresh}
<title>Kobo push</title>
<style>body{{font-family:sans-serif;max-width:40em;margin:2em auto;padding:0 1em}}
a.btn{{display:block;text-align:center;background:#2a9d8f;color:#fff;padding:1em;
border-radius:8px;text-decoration:none;font-size:1.3em;margin:1em 0}}
pre{{background:#f4f4f4;padding:1em;border-radius:8px;overflow-x:auto;font-size:.85em}}</style>
<h2>📚 → Kobo</h2>{body}"""


def running():
    return subprocess.run(
        ["systemctl", "--user", "is-active", "--quiet", "kobo-books-push.service"]
    ).returncode == 0


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, content, extra_headers=()):
        body = content.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in extra_headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/push":
            subprocess.run(["systemctl", "--user", "start", "--no-block", "kobo-books-push.service"])
            self.reply(303, "", [("Location", "/status")])
        elif self.path == "/status":
            log = html.escape(LOG.read_text()) if LOG.exists() else "(no log yet)"
            if running():
                body = f"<p>⏳ Push running… page refreshes itself.</p><pre>{log}</pre>"
                refresh = '<meta http-equiv="refresh" content="5">'
            else:
                body = f'<p>✅ Done. Latest run:</p><pre>{log}</pre><a class="btn" href="/push">Push again</a>'
                refresh = ""
            self.reply(200, PAGE.format(refresh=refresh, body=body))
        else:
            self.reply(200, PAGE.format(refresh="", body='<a class="btn" href="/push">Push library to Kobo Drive folder</a>'))

    def log_message(self, *args):
        pass


ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
