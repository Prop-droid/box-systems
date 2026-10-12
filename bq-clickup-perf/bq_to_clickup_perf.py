#!/usr/bin/env python3
"""
Write Meta ad performance back onto ClickUp tasks (ROAS / Spend / Orders /
Spend 30d / Last Active) so performance is sortable & filterable in ClickUp views.

Source = ejam-dwh.production.facebook_dashboard (Meta only; AppLovin/TikTok are
NOT in these fields by decision 2026-10-12). Not creative_dashboard: that table
drops Meta ads with no CAMS asset record (~10% of SHA Meta spend, e.g. SH-17273
showed $22.7k vs $118.6k real). Task key = creative_dashboard.clickup_project for
the ad_id when CAMS has one, else the first SH-#### in the ad name.

Every task on the Creative Strategist list with Meta spend is kept in sync, not
just recently active ones; only fields whose value changed are written, so a
normal run is a few hundred calls. Spend 30d drops to 0 when a task goes quiet.
Tasks with no Meta spend but leftover values get their fields cleared.

Cost: facebook_dashboard is partitioned on date_start but this is a lifetime
aggregate, so it scans ~8 GB (~$0.05/run). Keep the projection narrow; never
SELECT * (35M rows, big text columns).

Env:
    GOOGLE_APPLICATION_CREDENTIALS  BQ service account json (for the `bq` CLI)
    TOKEN_FILE                      ClickUp pk token file (default ~/.config/clickup/pk)
    PERF_DRY_RUN=1                  compute + print the diff, write nothing

Usage:
    PERF_DRY_RUN=1 python3 bq_to_clickup_perf.py     # preview
    python3 bq_to_clickup_perf.py                    # live write
"""
import http.client
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BQ_PROJECT = "ejam-dwh"
LIST_ID = "901110066469"
TEAM_ID = "9011638245"
BASE = "https://api.clickup.com/api/v2"
TOKEN_FILE = os.path.expanduser(os.environ.get("TOKEN_FILE", "~/.config/clickup/pk"))
DRY_RUN = os.environ.get("PERF_DRY_RUN") == "1"
REQUEST_TIMEOUT = 60
MAX_WORKERS = 5
# Guard: a broken/partial BQ result must never trigger mass field clearing.
MIN_BQ_PROJECTS = 1000

# field_id -> (row key, kind)  kind: "num" or "date_ms"
FIELDS = {
    "372c4db4-4e99-4f6a-b2c6-da27cc178182": ("roas_life", "num"),    # ROAS
    "c89e179f-ffe3-4374-85d4-a583b24402d1": ("spend_life", "num"),   # Spend
    "113fce5b-162d-4435-aaba-664910acf19a": ("orders_life", "num"),  # Orders
    "f232c84e-7afa-415d-9f70-22520495ce2c": ("spend_30d", "num"),    # Spend 30d
    "84b1b22b-9f72-4c3d-be98-b3ccbbdc3f11": ("last_active_ms", "date_ms"),  # Last Active
}

TOKEN = open(TOKEN_FILE).read().strip()

# Spend 30d = the last 30 complete days (today excluded, it is always partial).
BQ_SQL = r"""
WITH fb AS (
  SELECT CAST(ad_id AS STRING) AS ad_id,
    ANY_VALUE(ad_name) AS ad_name,
    SUM(spend) AS spend, SUM(revenue) AS revenue, SUM(orders) AS orders,
    SUM(IF(date_start BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
                          AND DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY), spend, 0)) AS spend_30d,
    MAX(IF(spend > 0, date_start, NULL)) AS last_active
  FROM `ejam-dwh.production.facebook_dashboard`
  WHERE brand = 'SHA' AND type = 'placement_breakdown' AND date_start >= '2020-01-01'
  GROUP BY ad_id
),
cd AS (
  SELECT CAST(ad_id AS STRING) AS ad_id, ANY_VALUE(clickup_project) AS clickup_project
  FROM `ejam-dwh.production.creative_dashboard`
  WHERE channel = 'facebook' AND clickup_project LIKE 'SH-%'
  GROUP BY ad_id
)
SELECT
  COALESCE(cd.clickup_project, REGEXP_EXTRACT(fb.ad_name, r'(SH-\d+)')) AS clickup_project,
  ROUND(SUM(fb.spend), 2) AS spend_life,
  ROUND(IFNULL(SAFE_DIVIDE(SUM(fb.revenue), NULLIF(SUM(fb.spend), 0)), 0), 2) AS roas_life,
  CAST(ROUND(IFNULL(SUM(fb.orders), 0)) AS INT64) AS orders_life,
  ROUND(SUM(fb.spend_30d), 2) AS spend_30d,
  CAST(UNIX_MILLIS(TIMESTAMP(MAX(fb.last_active))) AS INT64) AS last_active_ms
FROM fb LEFT JOIN cd USING (ad_id)
GROUP BY 1
HAVING clickup_project IS NOT NULL AND SUM(fb.spend) > 0
"""


def bq_rows():
    # SQL via stdin: bq parses a leading "--" in an argv query as a flag.
    out = subprocess.run(
        ["bq", f"--project_id={BQ_PROJECT}", "query", "--use_legacy_sql=false",
         "--format=json", "--max_rows=100000"],
        input=BQ_SQL, capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise RuntimeError(f"bq query failed:\n{out.stderr}")
    return json.loads(out.stdout or "[]")


def api(method, path, params=None, body=None, retries=4):
    url = f"{BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": TOKEN, "Content-Type": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return json.loads(resp.read() or "{}")
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            raise
        except (OSError, http.client.HTTPException):
            # OSError covers URLError, TimeoutError, ConnectionResetError;
            # HTTPException covers IncompleteRead / RemoteDisconnected.
            time.sleep(2 ** attempt)
            continue
    raise RuntimeError(f"Failed after {retries} retries: {method} {url}")


def list_tasks():
    """custom_id -> {field_id: current value} for every parent task on the list."""
    tasks = {}
    page = 0
    while True:
        resp = api("GET", f"/list/{LIST_ID}/task", {
            "page": page, "subtasks": "false",
            "include_closed": "true", "archived": "false",
        })
        batch = resp.get("tasks", [])
        if not batch:
            break
        for t in batch:
            if t.get("custom_id"):
                tasks[t["custom_id"]] = {
                    cf["id"]: cf.get("value") for cf in t.get("custom_fields", [])
                    if cf["id"] in FIELDS
                }
        if len(batch) < 100:
            break
        page += 1
    return tasks


def same(kind, current, target):
    if current in (None, ""):
        return False
    if kind == "date_ms":
        return int(current) // 86_400_000 == target // 86_400_000
    return abs(float(current) - target) < 0.005


def plan(tasks, rows):
    """List of (custom_id, field_id, value|None); None = clear the field."""
    by_cid = {r["clickup_project"]: r for r in rows}
    ops = []
    for cid, current in tasks.items():
        row = by_cid.get(cid)
        for field_id, (key, kind) in FIELDS.items():
            cur = current.get(field_id)
            if row is None or row.get(key) in (None, ""):
                if cur not in (None, ""):
                    ops.append((cid, field_id, None))
                continue
            target = int(row[key]) if kind == "date_ms" else float(row[key])
            if not same(kind, cur, target):
                ops.append((cid, field_id, target))
    return ops


def apply(op):
    cid, field_id, value = op
    params = {"custom_task_ids": "true", "team_id": TEAM_ID}
    if value is None:
        api("DELETE", f"/task/{cid}/field/{field_id}", params=params)
    else:
        api("POST", f"/task/{cid}/field/{field_id}", params=params, body={"value": value})
    return cid


def main():
    print(f"{'DRY RUN — ' if DRY_RUN else ''}BQ (Meta) -> ClickUp performance writeback")
    tasks = list_tasks()
    print(f"List {LIST_ID}: {len(tasks)} tasks")

    rows = bq_rows()
    print(f"BQ projects with Meta spend: {len(rows)}")
    if len(rows) < MIN_BQ_PROJECTS:
        raise SystemExit(f"ABORT: only {len(rows)} BQ projects (< {MIN_BQ_PROJECTS}); refusing to write")

    ops = plan(tasks, rows)
    clears = sum(1 for o in ops if o[2] is None)
    touched = len({o[0] for o in ops})
    print(f"Changed fields: {len(ops)} on {touched} tasks ({clears} clears)")

    on_list = {r["clickup_project"]: r for r in rows if r["clickup_project"] in tasks}
    print("\nTop 8 by 30d Meta spend:")
    for r in sorted(on_list.values(), key=lambda r: float(r["spend_30d"]), reverse=True)[:8]:
        print(f"  {r['clickup_project']}: ROAS {r['roas_life']} | Spend ${r['spend_life']} "
              f"| Orders {r['orders_life']} | 30d ${r['spend_30d']}")

    if DRY_RUN:
        print(f"\nDRY RUN: would make {len(ops)} field writes. No changes made.")
        return

    ok, errs = 0, []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futs = {pool.submit(apply, o): o for o in ops}
        for fut in as_completed(futs):
            try:
                fut.result()
                ok += 1
            except Exception as e:
                errs.append((futs[fut], str(e)))
            if (ok + len(errs)) % 500 == 0:
                print(f"  {ok + len(errs)}/{len(ops)} done", flush=True)

    print(f"\nDone. {ok} field writes, {len(errs)} errors.")
    for op, e in errs[:10]:
        print(f"  ERR {op[0]} {op[1][:8]}: {e}")
    if errs:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
