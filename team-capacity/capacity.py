"""Days off -> adjusted capacity. Pure given event lists; the gws pull lives in calendar_pull.py."""
from datetime import datetime, timedelta
import config as C
def person_from_event(summary, creator_email):
    s = (summary or "").lower(); em = (creator_email or "").lower().split("@")[0]
    for code, hints in C.NAME_HINTS.items():
        if any(h in s for h in hints) or any(h.strip() in em for h in hints if h.strip()): return code
    return None
def is_ooo(summary):
    s = (summary or "").lower(); return any(w in s for w in C.OOO_WORDS)
def event_days(start_date, end_date_excl):
    """all-day event dates (YYYY-MM-DD, end exclusive) -> list of weekday dates."""
    a = datetime.fromisoformat(start_date).date(); b = datetime.fromisoformat(end_date_excl).date() if end_date_excl else a + timedelta(days=1)
    return [a + timedelta(days=i) for i in range((b - a).days) if (a + timedelta(days=i)).weekday() < 5]
def days_off(ooo_events, holiday_events):
    """ooo_events: [(summary, creator_email, start_date, end_date_excl)]; holiday_events: [(code, summary, description, start_date, end_date_excl)]
    -> {code: [(date, hours, reason)]}"""
    out = {c: [] for c in C.POOL}
    for summary, creator, sd, ed in ooo_events:
        code = person_from_event(summary, creator)
        if not code or not is_ooo(summary): continue
        h = C.HALF_DAY_H if "half" in summary.lower() else C.DAY_H
        for d in event_days(sd, ed): out[code].append((d.isoformat(), h, summary))
    for code, summary, desc, sd, ed in holiday_events:
        if (desc or "").strip().split("\n")[0] != "Public holiday": continue
        for d in event_days(sd, ed): out[code].append((d.isoformat(), C.DAY_H, summary))
    for c in out:  # dedupe per date
        seen = {}; [seen.setdefault(d, (d, h, r)) for d, h, r in out[c]]; out[c] = sorted(seen.values())
    return out
def capacity(days):
    """{code: hours} after days off."""
    return {c: max(0.0, C.CAP_H - sum(h for _, h, _ in days.get(c, []))) for c in C.POOL}
