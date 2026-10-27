"""Week windows. ISO weeks, Europe/Vilnius. Window = [start, end] in ms epoch."""
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo
import config as C
TZ = ZoneInfo(C.TZ)
def ms(dt): return int(dt.timestamp() * 1000)
def from_ms(x): return datetime.fromtimestamp(x / 1000, TZ)
def monday_of(dt):
    d = dt.astimezone(TZ); return datetime.combine((d - timedelta(days=d.weekday())).date(), dtime(0, 0), TZ)
def iso_label(dt):
    y, w, _ = dt.astimezone(TZ).isocalendar(); return f"{y}-W{w:02d}", w
def window(now, last_end_ms=None):
    """Reported window: from last run end (or this ISO week's Monday 00:00) to now."""
    start = from_ms(last_end_ms + 1) if last_end_ms else monday_of(now)
    return ms(start), ms(now)
def next_week(now):
    """The week being planned at a Saturday run = next Monday 00:00 -> Sunday 23:59:59."""
    mon = monday_of(now) + timedelta(days=7)
    return ms(mon), ms(mon + timedelta(days=7)) - 1
def weekdays_1700(mon_ms):
    mon = from_ms(mon_ms)
    return [ms(datetime.combine((mon + timedelta(days=i)).date(), dtime(17, 0), TZ)) for i in range(5)]
def fmt_range(ws, we):
    a, b = from_ms(ws), from_ms(we)
    return f"{a.strftime('%b %d')} – {b.strftime('%b %d')}"
