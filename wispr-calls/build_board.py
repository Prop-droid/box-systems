#!/usr/bin/env python3
"""Build one self-contained HTML page from extracted/items.json.

Output: $WISPR_CALLS_DIR/board/index.html
serve.py serves the page and keeps the tick state on the box.

Focus rule (focus.json): the page leads with what Tomas owns, then what other
people owe him, then the creative team. All other items go to one closed block.
"""
import datetime
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("WISPR_CALLS_DIR", os.path.expanduser("~/.local/share/wispr-calls"))
E = html.escape

CSS = """
:root{--bg:#f5f4f0;--card:#fffefb;--ink:#1c1b19;--mute:#5f5d57;--line:#dedbd3;--acc:#0b5c8a;--warn:#8a4b00;--hover:#f0eee8;--chip:#eae8e1}
@media (prefers-color-scheme:dark){:root{--bg:#131312;--card:#1c1c1a;--ink:#edebe5;--mute:#a5a29a;--line:#33322d;--acc:#7cc4ee;--warn:#f0b35c;--hover:#252522;--chip:#292826}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;-webkit-text-size-adjust:100%}
.page{max-width:1180px;margin:0 auto;padding:0 16px 72px}
header{padding:28px 0 16px}
.eyebrow{margin:0;color:var(--mute);font-size:14px;font-weight:600}
h1{margin:2px 0 6px;font-size:clamp(40px,9vw,60px);line-height:1.02;letter-spacing:-.025em;font-weight:700;font-variant-numeric:tabular-nums}
h1 small{font-size:.42em;font-weight:500;letter-spacing:0;color:var(--mute);margin-left:.15em}
.sub{margin:0;color:var(--mute);font-size:14px}
.sub b{color:var(--warn);font-weight:600}
.warn{color:var(--warn);font-weight:600;margin-top:8px}
nav{position:sticky;top:0;z-index:2;background:var(--bg);border-bottom:1px solid var(--line);margin:0 -16px;padding:8px 16px;display:flex;gap:6px;flex-wrap:wrap;align-items:center}
nav a{color:var(--ink);text-decoration:none;background:var(--chip);padding:0 12px;border-radius:6px;font-size:14px;min-height:40px;display:inline-flex;align-items:center;gap:6px}
nav a:hover{background:var(--line)}
nav a b{font-variant-numeric:tabular-nums}
.tog{margin-left:auto;font-size:14px;color:var(--mute);display:inline-flex;gap:8px;align-items:center;min-height:40px;cursor:pointer}
input[type=checkbox]{width:20px;height:20px;margin:0;flex:none;accent-color:var(--acc);cursor:pointer}
a:focus-visible,summary:focus-visible,input:focus-visible{outline:2px solid var(--acc);outline-offset:2px;border-radius:4px}
section{margin-top:32px;scroll-margin-top:68px}
h2{font-size:20px;margin:0;letter-spacing:-.01em}
h2 .c{color:var(--mute);font-weight:500;font-variant-numeric:tabular-nums;margin-left:6px}
.note{color:var(--mute);font-size:14px;margin:2px 0 0;max-width:60ch}
h3{font-size:13px;margin:20px 0 6px;color:var(--mute);font-weight:600;display:flex;gap:10px;justify-content:space-between;align-items:baseline}
h3 .age{font-weight:500;white-space:nowrap}
.old{color:var(--warn);font-weight:600}
ul.items{list-style:none;margin:0;padding:0;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
ul.items li{border-top:1px solid var(--line)}
ul.items li:first-child{border-top:0}
ul.items label,ul.items .row{display:flex;gap:12px;padding:12px 14px;align-items:flex-start;min-height:48px}
ul.items label{cursor:pointer}
ul.items label:hover{background:var(--hover)}
ul.items input{margin-top:2px}
.t{flex:1;min-width:0;overflow-wrap:anywhere}
.m{display:block;color:var(--mute);font-size:13px;margin-top:2px}
.m strong{color:var(--ink);font-weight:600}
li.done .t{color:var(--mute);text-decoration:line-through}
li.done .m strong{color:inherit}
body.hide li.done{display:none}
.empty{color:var(--mute);font-size:14px;padding:14px;background:var(--card);border:1px solid var(--line);border-radius:10px;margin-top:10px}
details{margin-top:12px;border:1px solid var(--line);border-radius:10px;background:var(--card)}
details>summary{cursor:pointer;padding:0 14px;min-height:48px;display:flex;align-items:center;gap:8px;font-weight:600;list-style:none}
details>summary::-webkit-details-marker{display:none}
details>summary::before{content:"";width:7px;height:7px;border-right:2px solid var(--mute);border-bottom:2px solid var(--mute);transform:rotate(-45deg);transition:transform .15s;flex:none;margin-right:4px}
details[open]>summary::before{transform:rotate(45deg)}
details>summary:hover{background:var(--hover);border-radius:10px}
details>summary .c{color:var(--mute);font-weight:500;font-variant-numeric:tabular-nums}
details>.in{padding:0 14px 14px}
details ul.items{background:var(--bg)}
.wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:8px 10px;border-top:1px solid var(--line);vertical-align:top}
th{color:var(--mute);font-weight:600;border-top:0}
td.n{text-align:right;font-variant-numeric:tabular-nums}
.skip{color:var(--warn)}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
@media (min-width:960px){
 .page{padding:0 32px 96px}
 nav{margin:0 -32px;padding:8px 32px}
 header{padding:44px 0 20px}
 .cols{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(0,1fr);gap:48px;align-items:start}
}
"""

JS = """
let done={};const warn=document.getElementById('warn'),now=new Date();
const age=d=>Math.round((now-new Date(d+'T12:00:00Z'))/864e5);
function paint(){document.querySelectorAll('li[data-k]').forEach(li=>{const on=!!done[li.dataset.k];
 li.classList.toggle('done',on);li.querySelector('input').checked=on});
 document.querySelectorAll('[data-count]').forEach(b=>{const s=document.getElementById(b.dataset.count);
 b.textContent=s.querySelectorAll('li[data-k]:not(.done)').length});
 const open=[...document.querySelectorAll('#mine li[data-k]:not(.done)')];
 document.getElementById('nold').textContent=open.filter(li=>age(li.dataset.d)>=7).length;
 document.querySelectorAll('.grp').forEach(g=>{g.hidden=document.body.classList.contains('hide')&&!g.querySelector('li:not(.done)')})}
function send(k,on){return fetch('tick',{method:'POST',headers:{'Content-Type':'application/json'},
 body:JSON.stringify({k:k,done:on})}).then(r=>{if(!r.ok)throw 0;warn.hidden=true})
 .catch(()=>{warn.hidden=false})}
document.querySelectorAll('li[data-k] input').forEach(i=>i.addEventListener('change',e=>{
 const k=e.target.closest('li').dataset.k;if(e.target.checked)done[k]=1;else delete done[k];
 paint();send(k,e.target.checked)}));
document.querySelectorAll('[data-age]').forEach(s=>{const n=age(s.dataset.age);
 s.textContent=n<=0?'today':n===1?'1 day ago':n+' days ago';if(n>=7)s.classList.add('old')});
const hide=document.getElementById('hide');
try{hide.checked=localStorage.getItem('wispr-hide')==='1'}catch(e){}
document.body.classList.toggle('hide',hide.checked);
hide.addEventListener('change',e=>{document.body.classList.toggle('hide',e.target.checked);
 try{localStorage.setItem('wispr-hide',e.target.checked?'1':'0')}catch(x){};paint()});
fetch('state').then(r=>r.json()).then(s=>{done=s;paint()}).catch(()=>{warn.hidden=false;paint()});
"""


def day(d):
    return datetime.date.fromisoformat(d).strftime("%a %-d %b")


def li(it, meta="", tick=True):
    body = f'<span class="t">{E(it["text"])}{f"<span class=m>{meta}</span>" if meta else ""}</span>'
    if not tick:
        return f'<li><div class="row">{body}</div></li>'
    return (f'<li data-k="{it["key"]}" data-d="{E(it["date"])}"><label>'
            f'<input type="checkbox">{body}</label></li>')


def ul(items, meta=None, tick=True):
    return '<ul class="items">' + "".join(li(i, meta(i) if meta else "", tick) for i in items) + "</ul>"


def age(d):
    return f'<span class="age" data-age="{E(d)}"></span>'


def by_call(items, tick=True):
    """Group items under their call. Newest call first."""
    g = {}
    for i in items:
        g.setdefault((i["date"], i["call_title"]), []).append(i)
    return "".join(
        f'<div class="grp"><h3><span>{E(t)} · {day(dt)}</span>{age(dt)}</h3>{ul(v, tick=tick)}</div>'
        for (dt, t), v in sorted(g.items(), reverse=True))


def by_owner(items):
    g = {}
    for i in items:
        for o in i["owners"] or ["Owner not known"]:
            g.setdefault(o, []).append(i)
    src = lambda i: f'{E(i["call_title"])} · {age(i["date"])}'
    return "".join(
        f'<div class="grp"><h3><span>{E(o)}</span><span class="age">{len(v)}</span></h3>{ul(v, meta=src)}</div>'
        for o, v in sorted(g.items(), key=lambda kv: (-len(kv[1]), kv[0])))


def fold(title, n, inner, open_=False):
    return (f'<details{" open" if open_ else ""}><summary>{E(title)} <span class="c">{n}</span></summary>'
            f'<div class="in">{inner}</div></details>')


def main():
    d = json.load(open(os.path.join(BASE, "extracted", "items.json"), encoding="utf-8"))
    cfg = json.load(open(os.path.join(HERE, "focus.json"), encoding="utf-8"))
    me = re.compile(rf"\b{re.escape(cfg['me'])}\b")
    team = {n.lower() for n in cfg["team"]}
    on_team = lambda i: any(o.split()[0].lower() in team for o in i["owners"])

    calls, items = d["calls"], d["items"]
    mine, owed, pod, rest, dec = [], [], [], [], []
    for i in items:
        b = i["bucket"]
        if b == "mine":
            mine.append(i)
        elif b == "decision":
            dec.append(i)
        elif b in ("others", "unassigned") and me.search(i["text"]):
            owed.append(i)
        elif b == "everyone" or (b == "others" and on_team(i)):
            pod.append(i)
        else:
            rest.append(i)

    ok = [c for c in calls if c["state"] == "ok"]
    mins = sum(c["minutes"] for c in calls)
    now = datetime.datetime.now().strftime("%a %-d %b %H:%M")
    who = lambda i: (f'<strong>{E(", ".join(i["owners"]) or "Owner not known")}</strong> · '
                     f'{E(i["call_title"])} · {age(i["date"])}')

    rows = "".join(
        f'<tr><td>{E(c["date"])}</td><td>{E(c["title"])}</td><td class="n">{c["minutes"]}</td>'
        f'<td class="n">{c["next"]}</td>'
        f'<td>{E(", ".join(p for p in c["participants"] if p != "Tomas Šaltis")) or "-"}</td>'
        f'<td class="{"" if c["state"] == "ok" else "skip"}">{E(c["state"])}</td></tr>'
        for c in sorted(calls, key=lambda c: c["start_utc"], reverse=True))
    table = (f'<div class="wrap"><table><thead><tr><th>Date</th><th>Call</th><th>Min</th><th>Next</th>'
             f'<th>With</th><th>State</th></tr></thead><tbody>{rows}</tbody></table></div>')
    none = '<p class="empty">Nothing here.</p>'

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>Call follow-ups</title><style>{CSS}</style></head><body><div class="page">
<header><p class="eyebrow">Call follow-ups</p>
<h1><span data-count="mine">{len(mine)}</span><small>open for you</small></h1>
<p class="sub"><b><span id="nold">0</span> older than 7 days</b> · {len(ok)} calls, {mins // 60} h {mins % 60} min · synced {now}</p>
<p class="sub warn" id="warn" hidden>The box did not save the last tick. Reload the page.</p></header>
<nav><a href="#mine">Mine <b data-count="mine"></b></a><a href="#owed">Owed to me <b data-count="owed"></b></a>
<a href="#team">Team <b data-count="team"></b></a>
<label class="tog"><input type="checkbox" id="hide"> Hide done</label></nav>
<div class="cols">
<section id="mine"><h2>Mine</h2><p class="note">Next steps that you own. Newest call first.</p>
{by_call(mine) or none}</section>
<div>
<section id="owed"><h2>Owed to me</h2><p class="note">Next steps that other people own and that name you.</p>
{f'<div style="margin-top:14px">{ul(owed, meta=who)}</div>' if owed else none}</section>
<section id="team"><h2>Creative team</h2><p class="note">Next steps that your editors and designers own.</p>
{fold("Show team items", len(pod), by_owner(pod)) if pod else none}</section>
<section id="more"><h2>Reference</h2>
{fold("Decisions", len(dec), by_call(dec, tick=False))}
{fold("Not in focus", len(rest), '<p class="note">Next steps of people outside your team, and items with no known owner.</p>' + by_owner(rest))}
{fold("Calls", len(calls), table)}</section>
</div></div></div><script>{JS}</script></body></html>"""
    out = os.path.join(BASE, "board", "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp"
    open(tmp, "w", encoding="utf-8").write(page)
    os.replace(tmp, out)

    # Same focus split as data. The CCC /calls page reads this file.
    slim = lambda v: [{"key": i["key"], "text": i["text"], "owners": i["owners"],
                       "call": i["call_title"], "date": i["date"]} for i in v]
    data = {"built": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "calls": len(ok), "minutes": mins, "mine": slim(mine), "owed": slim(owed),
            "team": slim(pod), "rest": slim(rest), "decisions": slim(dec)}
    jout = os.path.join(BASE, "board", "board.json")
    json.dump(data, open(jout + ".tmp", "w", encoding="utf-8"), ensure_ascii=False)
    os.replace(jout + ".tmp", jout)
    print(f"wrote {out} bytes={len(page.encode())} mine={len(mine)} owed={len(owed)} team={len(pod)} "
          f"not_in_focus={len(rest)} decisions={len(dec)} calls={len(calls)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
