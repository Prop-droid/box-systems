"""Output count: OUTPUT line first (requested), Air unique-creative count as fallback (delivered)."""
import re, sys, os
import config as C
sys.path.insert(0, C.HERE)
OUT_RE = re.compile(r"OUTPUT[^\n\d]{0,20}(\d+)", re.I)
def output_line(task):
    d = task.get("markdown_description") or task.get("description") or ""
    m = OUT_RE.search(d)
    return int(m.group(1)) if m else None
def air_short_id(url):
    m = re.search(r"air\.inc/a/([A-Za-z0-9]+)", url or ""); return m.group(1) if m else None
def air_count(url, kind):
    try:
        import air_count as A
        r = A.count(air_short_id(url))
        return (r.get("unique_image") if kind == "img" else r.get("unique_video")) or 0, None
    except Exception as e:
        return 0, str(e)[:80]
