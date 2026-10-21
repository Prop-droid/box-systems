#!/usr/bin/env python3
"""Render pending.md as a self-contained HTML preview (Tomas 2026-10-21:
"always generate self improvement report html preview link").

Writes <share>/index.html (latest) + <share>/<date>.html (history) and prints
the tailnet URL. Served tailnet-only (not Funnel): the list carries internal
paths and incident notes. Tick boxes build the "self-improve: apply ..." reply.

Usage: build_preview.py [pending.md]   -> prints URL on stdout
"""
import html
import re
import sys
from pathlib import Path

import markdown

HOME = Path.home()
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HOME / "systems/self-improve/pending.md"
TOKEN = "0gruccjowlgxy5r"
SHARE = HOME / "systems/public-share" / TOKEN
URL = f"https://tomas-agent-box.tailb74909.ts.net/si/{TOKEN}/"

PROP_RE = re.compile(r"^### (P\d+):\s*(.+?)\s*(?:\[source:\s*(.+?)\])?\s*$")
FIELD_RE = re.compile(r"^-\s*(Evidence|Apply):\s*(.*)$")

CSS = """
:root{color-scheme:dark;--bg:#0d1117;--card:#161b22;--line:#30363d;--fg:#c9d1d9;
 --mut:#8b949e;--acc:#58a6ff;--ok:#3fb950}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:16px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:20px 16px 140px}
h1{font-size:1.5em;margin:.2em 0 .1em}
.sub{color:var(--mut);font-size:14px;margin-bottom:18px}
h2{font-size:1.15em;margin:1.8em 0 .6em;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0}
.card.on{border-color:var(--ok)}
.head{display:flex;gap:12px;align-items:flex-start}
.head input{width:22px;height:22px;margin-top:3px;flex:none;accent-color:var(--ok)}
.pid{font-weight:700;color:var(--acc);margin-right:6px}
.title{font-weight:600}
.src{display:inline-block;font-size:12px;color:var(--mut);border:1px solid var(--line);
 border-radius:20px;padding:1px 9px;margin-top:6px}
.f{margin-top:10px;font-size:15px}
.f b{color:var(--mut);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em;display:block}
code{background:#0d1117;border:1px solid var(--line);padding:.1em .35em;border-radius:5px;font-size:.88em;word-break:break-word}
.md ul{padding-left:1.2em}.md p{margin:.5em 0}
.bar{position:fixed;left:0;right:0;bottom:0;background:#010409;border-top:1px solid var(--line);padding:12px 16px}
.bar .in{max-width:860px;margin:0 auto;display:flex;gap:10px;align-items:center}
#cmd{flex:1;font:14px ui-monospace,Menlo,monospace;background:var(--card);color:var(--fg);
 border:1px solid var(--line);border-radius:8px;padding:10px}
button{font:600 14px inherit;background:var(--ok);color:#04130a;border:0;border-radius:8px;padding:10px 14px}
"""

JS = """
const boxes=[...document.querySelectorAll('input[data-p]')],cmd=document.getElementById('cmd');
function upd(){const on=boxes.filter(b=>b.checked).map(b=>b.dataset.p);
 boxes.forEach(b=>b.closest('.card').classList.toggle('on',b.checked));
 cmd.value=on.length?'self-improve: apply '+on.join(', '):'';}
boxes.forEach(b=>b.addEventListener('change',upd));
document.getElementById('cp').onclick=()=>{cmd.select();
 (navigator.clipboard?navigator.clipboard.writeText(cmd.value):Promise.reject())
 .catch(()=>document.execCommand('copy'));};
"""


def inline(s: str) -> str:
    """Escape, then restore `code` spans."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(s, quote=False))


def md(text: str) -> str:
    return markdown.markdown(text, extensions=["tables", "fenced_code"])


def parse(text: str):
    lines = text.splitlines()
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), "Self-improve pending")
    props, cur, rest, section = [], None, [], None
    for ln in lines:
        if ln.startswith("# "):
            continue
        if ln.startswith("## "):
            section = ln[3:].strip()
            cur = None
            if section.lower() != "proposals":
                rest.append(ln)
            continue
        m = PROP_RE.match(ln)
        if m and section and section.lower() == "proposals":
            cur = {"id": m.group(1), "title": m.group(2), "src": m.group(3) or "", "fields": []}
            props.append(cur)
            continue
        if cur is not None:
            f = FIELD_RE.match(ln)
            if f:
                cur["fields"].append([f.group(1), f.group(2)])
            elif ln.strip() and cur["fields"]:
                cur["fields"][-1][1] += " " + ln.strip()
            elif ln.strip():
                cur["fields"].append(["", ln.strip()])
            continue
        rest.append(ln)
    return title, props, "\n".join(rest)


def render(text: str) -> str:
    title, props, rest = parse(text)
    cards = []
    for p in props:
        fields = "".join(
            f'<div class="f">{"<b>" + k + "</b>" if k else ""}{inline(v)}</div>' for k, v in p["fields"]
        )
        src = f'<span class="src">{html.escape(p["src"])}</span>' if p["src"] else ""
        cards.append(
            f'<div class="card"><label class="head"><input type="checkbox" data-p="{p["id"]}">'
            f'<div><span class="pid">{p["id"]}</span><span class="title">{inline(p["title"])}</span>'
            f"<br>{src}</div></label>{fields}</div>"
        )
    body = (f"<h2>Proposals ({len(props)})</h2>" + "".join(cards)) if props else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head><body><div class="wrap">
<h1>{html.escape(title)}</h1>
<div class="sub">Tick items, copy the line, paste it in Discord #dev. Source: ~/systems/self-improve/pending.md</div>
{body}<div class="md">{md(rest)}</div></div>
<div class="bar"><div class="in"><input id="cmd" readonly placeholder="tick proposals to build the reply">
<button id="cp">Copy</button></div></div><script>{JS}</script></body></html>"""


def main():
    text = SRC.read_text()
    out = render(text)
    m = re.search(r"\d{4}-\d{2}-\d{2}", text.splitlines()[0] if text else "")
    SHARE.mkdir(parents=True, exist_ok=True)
    (SHARE / "index.html").write_text(out)
    if m:
        (SHARE / f"{m.group(0)}.html").write_text(out)
    print(URL)


if __name__ == "__main__":
    main()
