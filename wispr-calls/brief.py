#!/usr/bin/env python3
"""Print the morning-brief block: open call follow-ups that Tomas owns.

Prints nothing when there is nothing open, on Saturday and Sunday, or when the
data is missing. Used by ~/systems/ea-calendar/digest.py.
"""
import datetime
import json
import os
import sys

BASE = os.environ.get("WISPR_CALLS_DIR", os.path.expanduser("~/.local/share/wispr-calls"))
URL = os.environ.get("WISPR_BOARD_URL", "http://100.107.26.69:8099/")
OLD_DAYS, MAX_LINES = 7, 5


def main():
    today = datetime.date.today()
    if today.weekday() >= 5 and os.environ.get("WISPR_BRIEF_FORCE") != "1":
        return 0
    try:
        items = json.load(open(os.path.join(BASE, "extracted", "items.json"), encoding="utf-8"))["items"]
    except (OSError, ValueError, KeyError):
        return 0
    try:
        done = json.load(open(os.path.join(BASE, "state", "done.json"), encoding="utf-8"))
    except (OSError, ValueError):
        done = {}
    mine = [i for i in items if i["bucket"] == "mine" and i["key"] not in done]
    if not mine:
        return 0
    for i in mine:
        i["age"] = (today - datetime.date.fromisoformat(i["date"])).days
    old = sorted((i for i in mine if i["age"] >= OLD_DAYS), key=lambda i: -i["age"])
    lines = [f"**Call follow-ups** — {len(mine)} open for you, {len(old)} older than {OLD_DAYS} days"]
    for i in old[:MAX_LINES]:
        lines.append(f"  {i['age']}d  {i['text']}  ({i['call_title']})")
    if len(old) > MAX_LINES:
        lines.append(f"  and {len(old) - MAX_LINES} more")
    lines.append(f"  <{URL}>")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
