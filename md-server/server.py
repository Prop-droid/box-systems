#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["markdown>=3.6", "pygments>=2.17"]
# ///
"""Tiny read-only markdown browser for ~/brain.

Serves the brain tree as styled HTML over HTTP (intended for the Tailnet/LAN).
- Directories render as a browsable listing (folders + .md first).
- .md files render to GitHub-ish HTML (tables, fenced code, TOC).
- Other files are served raw. Path traversal outside ROOT is blocked.

Run: uv run server.py   (deps auto-installed by uv via the inline metadata)
Env: MD_ROOT (default ~/brain), MD_HOST (default 0.0.0.0), MD_PORT (default 8092)
"""
import html
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import markdown

ROOT = Path(os.environ.get("MD_ROOT", str(Path.home() / "brain"))).resolve()
HOST = os.environ.get("MD_HOST", "0.0.0.0")
PORT = int(os.environ.get("MD_PORT", "8092"))

CSS = """
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:#0d1117;color:#c9d1d9;
 font:16px/1.65 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:900px;margin:0 auto;padding:28px 20px 120px}
a{color:#58a6ff;text-decoration:none}a:hover{text-decoration:underline}
.crumb{font-size:13px;color:#8b949e;margin-bottom:22px;word-break:break-all}
.crumb a{color:#8b949e}
h1,h2,h3,h4{line-height:1.25;margin:1.4em 0 .5em;font-weight:600}
h1{font-size:1.9em;border-bottom:1px solid #21262d;padding-bottom:.3em}
h2{font-size:1.45em;border-bottom:1px solid #21262d;padding-bottom:.25em}
h3{font-size:1.2em}
table{border-collapse:collapse;width:100%;margin:1em 0;display:block;overflow-x:auto}
th,td{border:1px solid #30363d;padding:7px 12px;text-align:left;vertical-align:top}
th{background:#161b22}tr:nth-child(2n){background:#161b22}
code{background:#161b22;padding:.15em .4em;border-radius:5px;font-size:.88em}
pre{background:#161b22;padding:14px;border-radius:8px;overflow-x:auto}
pre code{background:none;padding:0}
blockquote{border-left:3px solid #30363d;margin:0;padding:.2em 1em;color:#8b949e}
hr{border:none;border-top:1px solid #21262d;margin:1.6em 0}
ul.list{list-style:none;padding:0}ul.list li{padding:4px 0;border-bottom:1px solid #161b22}
.dir{color:#e3b341}.md{color:#58a6ff}.file{color:#8b949e}
.tag{font-size:11px;color:#6e7681;margin-left:6px}
"""

MD_EXT = ["tables", "fenced_code", "codehilite", "toc", "attr_list", "sane_lists"]


def page(title, body):
    return (f"<!doctype html><html><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
            f"<body><div class=wrap>{body}</div></body></html>").encode()


def crumb(rel: Path):
    parts, acc, out = rel.parts, "", ["<a href='/'>brain</a>"]
    for p in parts:
        acc = f"{acc}/{p}" if acc else p
        out.append(f"<a href='/{urllib.parse.quote(acc)}'>{html.escape(p)}</a>")
    return "<div class=crumb>" + " / ".join(out) + "</div>"


def listing(target: Path, rel: Path):
    dirs, mds, files = [], [], []
    for c in sorted(target.iterdir(), key=lambda x: x.name.lower()):
        if c.name.startswith("."):
            continue
        href = "/" + urllib.parse.quote(str(c.relative_to(ROOT)))
        if c.is_dir():
            dirs.append(f"<li><a class=dir href='{href}'>📁 {html.escape(c.name)}</a></li>")
        elif c.suffix.lower() in (".md", ".markdown"):
            mds.append(f"<li><a class=md href='{href}'>📄 {html.escape(c.name)}</a></li>")
        else:
            files.append(f"<li><a class=file href='{href}'>{html.escape(c.name)}"
                         f"<span class=tag>raw</span></a></li>")
    items = "".join(dirs + mds + files) or "<li class=file>empty</li>"
    return page(rel.name or "brain",
                crumb(rel) + f"<ul class=list>{items}</ul>")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def send_html(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        rel_str = urllib.parse.unquote(self.path.split("?", 1)[0]).lstrip("/")
        target = (ROOT / rel_str).resolve()
        # block traversal outside ROOT
        if target != ROOT and ROOT not in target.parents:
            return self.send_html(page("403", "<h1>403</h1><p>Outside root.</p>"), 403)
        if not target.exists():
            return self.send_html(page("404", "<h1>404</h1>" + crumb(Path(rel_str))), 404)
        rel = target.relative_to(ROOT)
        if target.is_dir():
            return self.send_html(listing(target, rel))
        if target.suffix.lower() in (".md", ".markdown"):
            md = markdown.Markdown(extensions=MD_EXT)
            try:
                body = md.convert(target.read_text(encoding="utf-8", errors="replace"))
            except Exception as e:  # noqa: BLE001
                body = f"<pre>render error: {html.escape(str(e))}</pre>"
            return self.send_html(page(target.name, crumb(rel) + body))
        # raw file
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    print(f"md-server serving {ROOT} on http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()
