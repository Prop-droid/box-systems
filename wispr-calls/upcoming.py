#!/usr/bin/env python3
"""Write board/upcoming.json: Tomas's calls for the next 8 days, from the work calendar.

The CCC Calls page uses it for "Before your next calls". Attendee emails are
matched to the names Wispr gives the same people, so past calls can be joined.
A calendar failure keeps the last file and exits 0 (same rule as a sleeping Mac).
"""
import datetime
import json
import os
import subprocess
import sys
import unicodedata

BASE = os.environ.get("WISPR_CALLS_DIR", os.path.expanduser("~/.local/share/wispr-calls"))
GWS = os.path.expanduser("~/.local/bin/gws-work")  # work account: these are company calls
DAYS = 8


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s.lower() if "a" <= c <= "z")


def matcher(known):
    """known: full names from past calls. Returns f(email, display) -> full name or None."""
    full, firstlast, first = {}, {}, {}
    for name in known:
        parts = name.split()
        if not parts:
            continue
        full[norm(name)] = name
        firstlast[norm(parts[0] + parts[-1])] = name
        first.setdefault(norm(parts[0]), []).append(name)

    def find(email, display):
        for key in (norm(display), norm((email or "").split("@")[0])):
            if not key:
                continue
            if key in full:
                return full[key]
            if key in firstlast:
                return firstlast[key]
            if len(first.get(key, [])) == 1:  # a first name that only one known person has
                return first[key][0]
        return None

    return find


def label(a):
    if a.get("displayName"):
        return a["displayName"]
    return (a.get("email") or "?").split("@")[0]


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    params = {
        "calendarId": "primary", "singleEvents": True, "orderBy": "startTime", "maxResults": 150,
        "timeMin": now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
        "timeMax": (now + datetime.timedelta(days=DAYS)).isoformat(),
    }
    try:
        r = subprocess.run([GWS, "calendar", "events", "list", "--params", json.dumps(params)],
                           capture_output=True, text=True, timeout=60)
        raw = r.stdout[r.stdout.index("{"):]
        events = json.loads(raw).get("items", [])
    except Exception as e:  # noqa: BLE001 - keep the last file
        print(f"upcoming: calendar not read, last file kept ({type(e).__name__})")
        return 0

    try:
        calls = json.load(open(os.path.join(BASE, "extracted", "items.json"), encoding="utf-8"))["calls"]
    except (OSError, ValueError, KeyError):
        calls = []
    known = sorted({p for c in calls for p in c.get("participants") or []})
    find = matcher(known)

    out = []
    for e in events:
        start, end = e.get("start", {}).get("dateTime"), e.get("end", {}).get("dateTime")
        att = e.get("attendees") or []
        me = next((a for a in att if a.get("self")), None)
        others = [a for a in att if not a.get("self") and not a.get("resource")]
        if not start or not end or e.get("status") == "cancelled" or not others:
            continue  # all-day markers, cancelled, or no other person
        if me and me.get("responseStatus") == "declined":
            continue
        people, unknown = [], []
        for a in others:
            if a.get("responseStatus") == "declined":
                continue
            name = find(a.get("email"), a.get("displayName"))
            (people if name else unknown).append(name or label(a))
        out.append({"id": e.get("id") or f"{start}|{e.get('summary')}", "title": e.get("summary") or "(no title)",
                    "start": start, "end": end, "people": sorted(set(people)), "others": unknown})

    path = os.path.join(BASE, "board", "upcoming.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump({"built": now.isoformat(timespec="seconds"), "events": out}, f, ensure_ascii=False)
    os.replace(path + ".tmp", path)
    print(f"upcoming: {len(out)} calls, {sum(1 for x in out if x['people'])} with known people")
    return 0


if __name__ == "__main__":
    sys.exit(main())
