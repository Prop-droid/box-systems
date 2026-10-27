"""gws-work calendar pulls (work account). Strips the 'Using keyring' stdout line."""
import json, subprocess, urllib.parse
import config as C
def _events(cal_id, tmin_iso, tmax_iso):
    params = json.dumps({"calendarId": cal_id, "timeMin": tmin_iso, "timeMax": tmax_iso, "singleEvents": True, "maxResults": 250})
    p = subprocess.run([C.GWS, "calendar", "events", "list", "--params", params], capture_output=True, text=True, timeout=120)
    raw = "\n".join(l for l in p.stdout.splitlines() if not l.startswith("Using keyring"))
    if p.returncode != 0 or not raw.strip(): raise RuntimeError(f"gws calendar {cal_id}: rc={p.returncode} {p.stderr[-200:]}")
    return json.load(__import__("io").StringIO(raw)).get("items", [])
def _dates(ev):
    s = ev.get("start", {}); e = ev.get("end", {})
    sd = s.get("date") or s.get("dateTime", "")[:10]; ed = e.get("date") or (e.get("dateTime", "")[:10] if e.get("dateTime") else None)
    if not s.get("date") and ed == sd: ed = None  # timed event, same day
    return sd, ed
def pull(tmin_iso, tmax_iso):
    ooo = [(ev.get("summary"), (ev.get("creator") or {}).get("email"), *_dates(ev)) for ev in _events("primary", tmin_iso, tmax_iso)]
    hol = []
    for feed in sorted(set(C.HOLIDAY_FEEDS.values())):
        items = _events(feed + C.FEED_SUFFIX, tmin_iso, tmax_iso)
        for code, f in C.HOLIDAY_FEEDS.items():
            if f == feed:
                hol += [(code, ev.get("summary"), ev.get("description"), *_dates(ev)) for ev in items]
    return ooo, hol
