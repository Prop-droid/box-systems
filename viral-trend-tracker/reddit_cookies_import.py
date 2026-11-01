#!/usr/bin/env python3
"""Refresh the rdt (Reddit CLI) credential from a browser cookie export, headless.

The VTT reddit lane authenticates through ~/.local/bin/rdt, whose cookies come
from a logged-in browser. The box has no browser login, and anonymous
search.json is 403 from here (checked 2026-11-01, stealth browser included), so
when Reddit rejects the saved cookies ("forbidden") the only fix is a fresh
export from Tomas's browser. Usage, from the Mac, after Cookie-Editor on
reddit.com -> Export -> JSON (lands on the clipboard):

    pbpaste | ssh tomas-agent-box 'python3 ~/systems/viral-trend-tracker/reddit_cookies_import.py'

Accepts the Cookie-Editor array ([{name, value, ...}]) or a plain {name: value}
dict on stdin. Writes ~/.config/rdt-cli/credential.json (0600), then proves it
with `rdt status` + one search. Never prints cookie values.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

CRED = Path(os.path.expanduser("~/.config/rdt-cli/credential.json"))
RDT = os.path.expanduser("~/.local/bin/rdt")
REQUIRED = {"reddit_session"}


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        sys.exit("no input on stdin — pipe the Cookie-Editor JSON export")
    data = json.loads(raw)
    if isinstance(data, list):
        cookies = {c["name"]: c["value"] for c in data if isinstance(c, dict) and "name" in c and "value" in c
                   and "reddit" in str(c.get("domain", "reddit"))}
    elif isinstance(data, dict) and "cookies" in data and isinstance(data["cookies"], dict):
        cookies = dict(data["cookies"])
    elif isinstance(data, dict):
        cookies = {k: str(v) for k, v in data.items()}
    else:
        sys.exit("unrecognized JSON shape")
    missing = REQUIRED - set(cookies)
    if missing:
        sys.exit(f"export lacks {sorted(missing)} — is the browser logged in to reddit.com?")
    prev = {}
    if CRED.exists():
        try:
            prev = json.loads(CRED.read_text())
        except json.JSONDecodeError:
            prev = {}
        CRED.with_suffix(".json.bak").write_text(CRED.read_text())
        os.chmod(CRED.with_suffix(".json.bak"), 0o600)
    cred = {**prev, "cookies": cookies, "source": "cookie-editor-import", "saved_at": time.time(),
            "last_verified_at": None}
    CRED.parent.mkdir(parents=True, exist_ok=True)
    CRED.write_text(json.dumps(cred, indent=2))
    os.chmod(CRED, 0o600)
    print(f"wrote {CRED} with {len(cookies)} cookies (backup: {CRED.with_suffix('.json.bak').name})")
    st = subprocess.run([RDT, "status"], capture_output=True, text=True, timeout=60)
    print("rdt status:", " ".join(l.strip() for l in st.stdout.splitlines() if "authenticated" in l or "username" in l))
    sr = subprocess.run([RDT, "search", "fiber gummies", "-t", "week", "-n", "3", "--json"],
                        capture_output=True, text=True, timeout=60)
    try:
        payload = json.loads(sr.stdout)
        if payload.get("ok") is False:
            sys.exit(f"search still failing: {payload.get('error')}")
        n = len(payload["data"]["data"]["children"])
        print(f"search OK: {n} results. Now: systemctl --user start vtt-ingest.service")
    except (json.JSONDecodeError, KeyError) as e:
        sys.exit(f"search returned an unexpected payload ({e}): {sr.stdout[:200]} {sr.stderr[:200]}")


if __name__ == "__main__":
    main()
