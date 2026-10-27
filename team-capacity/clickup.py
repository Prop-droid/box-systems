"""Thin ClickUp REST v2 client. pk token at ~/.config/clickup/pk. Writes are date/tag/field/status/comment only."""
import json, os, time, urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor
import config as C
BASE = "https://api.clickup.com/api/v2"
class ClickUpError(Exception): pass
def _tok():
    return open(os.path.expanduser("~/.config/clickup/pk")).read().strip()
def req(method, path, body=None, params=None, retries=8):
    url = BASE + path + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
    data = json.dumps(body).encode() if body is not None else None
    for i in range(retries):
        r = urllib.request.Request(url, data=data, method=method, headers={"Authorization": _tok(), "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=90) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(min(60, 5 * (i + 1))); continue
            raise ClickUpError(f"{method} {path} -> {e.code} {e.read()[:200]!r}")
        except (urllib.error.URLError, TimeoutError):
            time.sleep(5)
    raise ClickUpError(f"{method} {path} -> gave up after {retries} tries")
def list_tasks(updated_since_ms, statuses=None):
    out, page = [], 0
    while True:
        p = {"page": page, "include_closed": "true", "subtasks": "true", "include_markdown_description": "true",
             "date_updated_gt": int(updated_since_ms)}
        if statuses: p["statuses[]"] = statuses
        d = req("GET", f"/list/{C.LIST_ID}/task", params=p)
        out += d.get("tasks", [])
        if d.get("last_page") or not d.get("tasks"): break
        page += 1
    return out
def bulk_time_in_status(task_ids):
    hist = {}
    for i in range(0, len(task_ids), 100):
        chunk = task_ids[i:i + 100]
        d = req("GET", "/task/bulk_time_in_status/task_ids?" + "&".join("task_ids=" + x for x in chunk))
        hist.update(d)
    return hist
def task_intervals(task_id):
    """-> [(user_id, start_ms, end_ms, source)]. Intervals are NESTED per user; start/end are strings."""
    d = req("GET", f"/task/{task_id}/time")
    out = []
    for u in d.get("data", []):
        uid = (u.get("user") or {}).get("id")
        for iv in u.get("intervals", []):
            s, e = int(iv.get("start") or 0), int(iv.get("end") or 0)
            if s and e: out.append((uid, s, e, iv.get("source")))
    return out
def intervals_for(tasks, threads=6):
    with ThreadPoolExecutor(threads) as ex:
        res = list(ex.map(lambda t: (t["id"], task_intervals(t["id"])), tasks))
    return dict(res)
def list_fields():
    return req("GET", f"/list/{C.LIST_ID}/field").get("fields", [])
def create_number_field(name):
    return req("POST", f"/list/{C.LIST_ID}/field", {"name": name, "type": "number"})
def set_field(task_id, field_id, value):
    return req("POST", f"/task/{task_id}/field/{field_id}", {"value": value})
def update_task(task_id, payload):
    return req("PUT", f"/task/{task_id}", payload)
def add_tag(task_id, tag):
    return req("POST", f"/task/{task_id}/tag/{urllib.parse.quote(tag)}")
def comment(task_id, text, assignee=None):
    body = {"comment_text": text, "notify_all": False}
    if assignee: body["assignee"] = assignee
    return req("POST", f"/task/{task_id}/comment", body)
