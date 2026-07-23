#!/usr/bin/env python3
"""Launch-details scanner: find tasks AND subtasks missing FB launch fields.

Read-only sibling of ~/systems/launch-autofill (which auto-WROTE fields and was
retired 2026-06-15). This one never writes to ClickUp: it scans the Creative
Strategist list for tasks in launch-relevant statuses whose FB launch fields
(LP / FB Page / Headline / Text) are empty — the "Ryan has to ask for launch
details" gap — and reports:

  - reports/latest.md (+ dated copy) every run
  - one ntfy push to Tomas's phone ONLY when a task newly appears in the
    missing set (state.json remembers what was already reported — no daily nag)

Unlike the autofill cron, SUBTASKS ARE IN SCOPE (talent THT cuts like
"[Lindsay Ortega] - SHA_..." live as subtasks and are exactly the ones media
buyers chase). ClickBot automation subtasks (Applovin/TikTok/FB scaling etc.)
stay excluded — other teams' jurisdiction (Tomas, 2026-06-12).

Env: SCAN_DRY=1 (print only, no push/state), SCAN_ALWAYS_PUSH=1,
     SCAN_LOOKBACK_DAYS (default 45), SCAN_STATUSES (comma-separated override).
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM_ID = "9011638245"
LIST_ID = "901110066469"
NTFY_TOPIC = "tomas-ph-1ea8ac8e"
STATE = HERE / "state.json"
REPORTS = HERE / "reports"
LOG = HERE / "logs" / "scan.log"

DRY = os.environ.get("SCAN_DRY") == "1"
ALWAYS_PUSH = os.environ.get("SCAN_ALWAYS_PUSH") == "1"
LOOKBACK_DAYS = int(os.environ.get("SCAN_LOOKBACK_DAYS", "45"))
STATUSES = [s.strip() for s in os.environ.get(
    "SCAN_STATUSES", "approved,sent to mb").split(",")]

# The 4 launch fields (see project_sha_launch_details_fill / autofill.py F dict)
FIELDS = {
    "LP":       "7eca3451-c4df-4897-a543-c92a3d04ede6",   # FB Ad3 - LP
    "FB Page":  "77e384fd-202e-47cf-9ef6-5b9b2d7aa36f",   # FB Ad4 - FB Page
    "Headline": "5a13da3d-3644-44d5-bf25-2af39ee2b661",   # FB Ad6 - Headline
    "Text":     "580b7f41-99f5-4c9f-a721-d59f6d2c4e48",   # FB Ad7 - Text
}

# ClickBot channel-distribution subtask names — never report these
EXCLUDE_NAME = re.compile(
    r"applovin|tiktok|facebook\s*-|bc/cc|retargeting|scaling|-\s*cpp", re.I)


def log(msg):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
    with LOG.open("a") as f:
        f.write(line + "\n")
    print(line)


def token():
    env = HERE / ".env"
    if env.exists():
        m = re.search(r"pk_[0-9]+_[A-Z0-9]{24,}", env.read_text())
        if m:
            return m.group(0)
    # fallback: recover from the retired autofill dir
    for p in (HERE.parent / "launch-autofill").glob("*"):
        try:
            m = re.search(r"pk_[0-9]+_[A-Z0-9]{24,}", p.read_text())
        except Exception:
            continue
        if m:
            return m.group(0)
    sys.exit("no ClickUp token found")


def api(path, params):
    qs = urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(
        f"https://api.clickup.com/api/v2{path}?{qs}",
        headers={"Authorization": token()})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def fetch():
    # TEAM endpoint: statuses[] applies to subtasks too (the LIST endpoint
    # ignores it for subtasks — that's the 5k-task trap from 2026-06-11)
    since_ms = int((time.time() - LOOKBACK_DAYS * 86400) * 1000)
    tasks, page = [], 0
    while True:
        r = api(f"/team/{TEAM_ID}/task", {
            "list_ids[]": LIST_ID, "statuses[]": STATUSES,
            "subtasks": "true", "include_closed": "false",
            "date_updated_gt": since_ms, "page": page})
        got = r.get("tasks", [])
        if not got:
            break
        tasks += got
        if r.get("last_page", len(got) < 100):
            break
        page += 1
    return [t for t in tasks
            if t.get("status", {}).get("status", "").lower() in STATUSES
            and (t.get("creator") or {}).get("username") != "ClickBot"
            and not EXCLUDE_NAME.search(t.get("name", ""))
            # only ad-launch work carries launch details — the SHA_ naming
            # convention marks it (ops tasks like "Video trim resize" don't)
            and "SHA_" in t.get("name", "")]


def empty(task, fid):
    for f in task.get("custom_fields", []):
        if f["id"] == fid:
            return f.get("value") in (None, "", [], {})
    return True


def main():
    found = []
    for t in fetch():
        missing = [label for label, fid in FIELDS.items() if empty(t, fid)]
        if missing:
            found.append({
                "id": t["id"],
                "custom_id": t.get("custom_id") or t["id"],
                "name": t["name"],
                "status": t.get("status", {}).get("status", "?"),
                "subtask": bool(t.get("parent")),
                "missing": missing,
                "url": t.get("url", f"https://app.clickup.com/t/{t['id']}"),
            })
    found.sort(key=lambda x: x["custom_id"])

    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# Launch details scan — {today}",
             f"Statuses: {', '.join(STATUSES)} · lookback {LOOKBACK_DAYS}d · "
             f"{len(found)} task(s) missing launch details", ""]
    for x in found:
        kind = "subtask" if x["subtask"] else "task"
        lines.append(f"- **{x['custom_id']}** ({x['status']}, {kind}) "
                     f"[{x['name']}]({x['url']}) — missing: {', '.join(x['missing'])}")
    report = "\n".join(lines) + "\n"
    if not DRY:
        REPORTS.mkdir(parents=True, exist_ok=True)
        (REPORTS / "latest.md").write_text(report)
        (REPORTS / f"{today}.md").write_text(report)

    prev = set()
    if STATE.exists():
        try:
            prev = set(json.loads(STATE.read_text()))
        except Exception:
            pass
    current = {x["id"] for x in found}
    new = current - prev
    log(f"scanned: {len(found)} missing ({len(new)} new) [dry={DRY}]")

    if DRY:
        print(report)
        return
    STATE.write_text(json.dumps(sorted(current)))

    if new or (ALWAYS_PUSH and found):
        top = [x for x in found if x["id"] in new] or found
        body = "\n".join(
            f"{x['custom_id']} missing {', '.join(x['missing'])}\n{x['url']}"
            for x in top[:8])
        if len(top) > 8:
            body += f"\n(+{len(top) - 8} more in reports/latest.md)"
        req = urllib.request.Request(
            f"https://ntfy.sh/{NTFY_TOPIC}", data=body.encode(),
            headers={"Title": f"Launch details missing: {len(found)} task(s)",
                     "Tags": "rocket"})
        try:
            urllib.request.urlopen(req, timeout=20)
            log(f"pushed ntfy ({len(top)} listed)")
        except Exception as e:
            log(f"ntfy push failed: {e}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"ERROR: {e}")
        sys.exit(1)
