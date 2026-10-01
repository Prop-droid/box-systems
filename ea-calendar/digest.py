#!/usr/bin/env python3
"""EA daily calendar digest: today + tomorrow, posted to the EA Telegram group 08:00.

Source of truth is the PERSONAL Google account token (~/tablet-assistant/token_personal.json)
because the ejam work calendar is mirrored into it — one token covers both. Aggregates
every selected calendar (primary, work mirror, holidays, Shameless Product Launch), dedupes
shared events by (title, start), and prints a plaintext two-day list.

Env: EA_CAL_DRY=1 (print only, no Telegram post).
Run: ~/systems/ea-calendar/run_digest.sh   (systemd: ea-calendar.timer, daily 08:00)
"""
import datetime
import os
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, "/home/tomas/tablet-assistant")
from google.oauth2.credentials import Credentials          # noqa: E402
from google.auth.transport.requests import Request         # noqa: E402
from googleapiclient.discovery import build                # noqa: E402

TZ = ZoneInfo("Europe/Vilnius")
TOKEN = Path("/home/tomas/tablet-assistant/token_personal.json")
HERE = Path(__file__).resolve().parent
LOG = HERE / "logs" / "digest.log"
DRY = os.environ.get("EA_CAL_DRY") == "1"


def log(msg):
    line = f"{datetime.datetime.now(TZ):%Y-%m-%dT%H:%M:%S} {msg}"
    print(line)
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def creds():
    c = Credentials.from_authorized_user_file(str(TOKEN))
    if c.expired and c.refresh_token:
        c.refresh(Request())
        TOKEN.write_text(c.to_json())
    return c


def fetch(day_start, end):
    cal = build("calendar", "v3", credentials=creds())
    ids = ["primary"]
    try:
        for c in cal.calendarList().list().execute().get("items", []):
            if c.get("selected", True) and c["id"] not in ids:
                ids.append(c["id"])
    except Exception as e:
        log(f"calendarList failed, primary only: {e}")
    raw = []
    for cid in ids:
        try:
            raw += cal.events().list(
                calendarId=cid, timeMin=day_start.isoformat(), timeMax=end.isoformat(),
                singleEvents=True, orderBy="startTime", maxResults=100,
            ).execute().get("items", [])
        except Exception as e:
            log(f"events.list {cid} failed: {e}")
    seen, out = set(), []
    for e in raw:
        st = e.get("start", {})
        key = (e.get("summary", ""), st.get("dateTime") or st.get("date"))
        if key in seen or e.get("status") == "cancelled":
            continue
        seen.add(key)
        if "dateTime" in st:
            dt = datetime.datetime.fromisoformat(st["dateTime"]).astimezone(TZ)
            time_s, sort, day = dt.strftime("%H:%M"), dt.isoformat(), dt.date()
        else:
            ds = st.get("date", "")
            day = datetime.date.fromisoformat(ds) if ds else day_start.date()
            time_s, sort = "all-day", (ds or day.isoformat())
        loc = e.get("location", "") or ("Meet" if e.get("hangoutLink") else "")
        out.append({"day": day, "time": time_s, "sort": sort,
                    "title": e.get("summary", "(no title)"), "loc": loc.split(",")[0][:40]})
    out.sort(key=lambda x: (x["day"], x["time"] == "all-day" and "0" or "1", x["sort"]))
    return out


def render(events, today, tomorrow):
    lines = [f"**Calendar — {today:%a %b %-d}**", ""]
    for day, label in ((today, f"Today ({today:%a %-d})"), (tomorrow, f"Tomorrow ({tomorrow:%a %-d})")):
        todays = [e for e in events if e["day"] == day]
        lines.append(f"{label}")
        if not todays:
            lines.append("  nothing scheduled")
        for e in todays:
            tail = f"  ({e['loc']})" if e["loc"] else ""
            lines.append(f"  {e['time']}  {e['title']}{tail}")
        lines.append("")
    return "\n".join(lines).strip()


def post(body):
    if DRY:
        log("dry run, not posting")
        return
    subprocess.run(
        ["bash", "/home/tomas/systems/lib/tg-post.sh", "🗓 Daily Calendar", "tg-ea-bot"],
        input=body.encode(), timeout=60, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    log("posted to EA group")


def main():
    now = datetime.datetime.now(TZ)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = day_start + datetime.timedelta(days=2)
    events = fetch(day_start, end)
    body = render(events, day_start.date(), (day_start + datetime.timedelta(days=1)).date())
    log(f"events today+tomorrow: {len(events)}")
    print(body)
    post(body)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"FAILED: {e}")
        raise
