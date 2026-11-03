#!/usr/bin/env python3
"""Monday 07:00 Vilnius: email the latest weekly report (computed Saturday by run_weekly.py) to settings.json `email_to`.
Flags: --label 2026-W44 (default: state.last_label) --to a@x,b@y (override list) --subject-prefix "[TEST] " --dry-run (gws --dry-run, no send) --force (resend an already-emailed label).
Guards: refuses a stale report (label != last ISO week) and never emails the same label twice unless --force. Failures -> ops-log alert + non-zero exit (watchdog)."""
import argparse, json, os, sys, subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as C, weeks as W
TZ = ZoneInfo(C.TZ)
def alert(title, body):
    subprocess.run([os.path.expanduser("~/systems/lib/tg-notify.sh"), title, body, "high"], capture_output=True, timeout=60)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--label"); ap.add_argument("--to"); ap.add_argument("--subject-prefix", default="")
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--force", action="store_true"); a = ap.parse_args()
    S = C.settings(); now = datetime.now(TZ)
    state = json.load(open(C.STATE)) if os.path.exists(C.STATE) else {}
    to = [x.strip() for x in (a.to.split(",") if a.to else S.get("email_to") or []) if x.strip()]
    if not to: print("email_to empty; nothing to send"); return
    label = a.label or state.get("last_label")
    expected, _ = W.iso_label(now - timedelta(days=7))
    if not label: alert("team-capacity send: no report yet", "state.json has no last_label"); sys.exit(2)
    if not a.label and label != expected:
        alert("team-capacity send: stale report, NOT emailed", f"latest computed {label}, expected {expected} (Saturday run missing?)"); print("STALE", label, expected); sys.exit(2)
    if not a.force and not a.dry_run and state.get("last_emailed_label") == label and not a.to:
        print(f"{label} already emailed {state.get('last_emailed_at')}; use --force"); return
    path = os.path.join(C.REPORT_DIR, f"{label}.txt")
    if not os.path.exists(path): alert("team-capacity send: report file missing", path); sys.exit(2)
    text = open(path).read().strip()
    first = text.splitlines()[0] if text else label           # "WEEK SPRINT S44 (Oct 26 – Oct 31)"
    sprint = first.replace("WEEK SPRINT ", "").strip() if first.startswith("WEEK SPRINT") else label
    subject = f"{a.subject_prefix}SHA creative team weekly report {sprint}"
    body = text
    if S.get("doc_id") and S.get("email_doc_link"):
        body += f"\n\nFull history: https://docs.google.com/document/d/{S['doc_id']}/edit"
    cmd = [C.GWS, "gmail", "+send", "--to", ",".join(to), "--subject", subject, "--body", body]
    if a.dry_run: cmd.append("--dry-run")
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    out = "\n".join(l for l in (p.stdout + p.stderr).splitlines() if "keyring" not in l.lower())
    print(f"[{now:%F %T}] {label} -> {', '.join(to)} subject={subject!r} rc={p.returncode} dry_run={a.dry_run}")
    print(out[-600:])
    if p.returncode != 0:
        alert("team-capacity send: email FAILED", f"{label} -> {', '.join(to)}\n{out[-700:]}"); sys.exit(1)
    if not a.dry_run and not a.to:
        state.update({"last_emailed_label": label, "last_emailed_at": now.isoformat(), "last_emailed_to": to}); json.dump(state, open(C.STATE, "w"), indent=1)
if __name__ == "__main__": main()
