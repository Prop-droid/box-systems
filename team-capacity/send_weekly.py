#!/usr/bin/env python3
"""Monday 07:00 Vilnius: DM the latest weekly report (computed Saturday by run_weekly.py) into ClickUp Chat.
Default target = settings.json `dm_channel` (Tomas <-> Katherine Guerra DM, posted as Tomas via the pk token). Tomas 2026-11-03: "not an email but dm message".
Flags: --label 2026-W44 (default: state.last_label) --channel <chat channel id> (override, never marks state) --subject-prefix "[TEST] "
       --email a@x,b@y (opt-in email via gws-work instead of chat) --dry-run (print, no post) --force (resend an already-sent label).
Guards: refuses a stale report (label != last ISO week) and never posts the same label twice unless --force. Failures -> ops-log alert + non-zero exit (watchdog)."""
import argparse, json, os, sys, subprocess, urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as C, weeks as W
TZ = ZoneInfo(C.TZ); WS = C.TEAM_ID
def alert(title, body):
    subprocess.run([os.path.expanduser("~/systems/lib/tg-notify.sh"), title, body, "high"], capture_output=True, timeout=60)
def chat_post(channel, text):
    tok = open(os.path.expanduser("~/.config/clickup/pk")).read().strip()
    body = json.dumps({"type": "message", "content_format": "text/md", "content": text}).encode()
    req = urllib.request.Request(f"https://api.clickup.com/api/v3/workspaces/{WS}/chat/channels/{channel}/messages", data=body, method="POST",
                                 headers={"Authorization": tok, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r: out = json.load(r)
    return (out.get("data") or {}).get("id") or out.get("id")
def email_send(to, subject, text):
    p = subprocess.run([C.GWS, "gmail", "+send", "--to", ",".join(to), "--subject", subject, "--body", text], capture_output=True, text=True, timeout=120)
    out = "\n".join(l for l in (p.stdout + p.stderr).splitlines() if "keyring" not in l.lower())
    if p.returncode != 0: raise RuntimeError(out[-600:])
    return out[-200:]
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--label"); ap.add_argument("--channel"); ap.add_argument("--email"); ap.add_argument("--subject-prefix", default="")
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--force", action="store_true"); a = ap.parse_args()
    S = C.settings(); now = datetime.now(TZ)
    state = json.load(open(C.STATE)) if os.path.exists(C.STATE) else {}
    channel = a.channel or S.get("dm_channel")
    if not channel and not a.email: print("dm_channel empty; nothing to send"); return
    label = a.label or state.get("last_label")
    expected, _ = W.iso_label(now - timedelta(days=7))
    if not label: alert("team-capacity send: no report yet", "state.json has no last_label"); sys.exit(2)
    if not a.label and label != expected:
        alert("team-capacity send: stale report, NOT sent", f"latest computed {label}, expected {expected} (Saturday run missing?)"); print("STALE", label, expected); sys.exit(2)
    override = bool(a.channel or a.email or a.label)
    if not a.force and not a.dry_run and not override and state.get("last_sent_label") == label:
        print(f"{label} already sent {state.get('last_sent_at')}; use --force"); return
    path = os.path.join(C.REPORT_DIR, f"{label}.txt")
    if not os.path.exists(path): alert("team-capacity send: report file missing", path); sys.exit(2)
    text = open(path).read().strip()
    first = text.splitlines()[0] if text else label           # "WEEK SPRINT S44 (Oct 26 – Oct 31)"
    sprint = first.replace("WEEK SPRINT ", "").strip() if first.startswith("WEEK SPRINT") else label
    subject = f"{a.subject_prefix}SHA creative team weekly report {sprint}"
    msg = (f"{a.subject_prefix}**{first}**\n" + "\n".join(text.splitlines()[1:])).strip()   # bold header line for chat
    target = f"email {a.email}" if a.email else f"chat {channel}"
    print(f"[{now:%F %T}] {label} -> {target} dry_run={a.dry_run} chars={len(msg)}")
    if a.dry_run: print(msg[:400] + ("\n..." if len(msg) > 400 else "")); return
    try:
        if a.email: res = email_send([x.strip() for x in a.email.split(",") if x.strip()], subject, text)
        else: res = f"message id={chat_post(channel, msg)}"
    except Exception as e:
        alert("team-capacity send: FAILED", f"{label} -> {target}\n{str(e)[-700:]}"); print("FAIL", e); sys.exit(1)
    print(res)
    if not override:
        state.update({"last_sent_label": label, "last_sent_at": now.isoformat(), "last_sent_to": target}); json.dump(state, open(C.STATE, "w"), indent=1)
if __name__ == "__main__": main()
