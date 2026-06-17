#!/usr/bin/env python3
"""
Write BigQuery ad performance back onto ClickUp tasks (ROAS / Spend / Orders /
Spend 30d / Last Active) so performance is sortable & filterable in ClickUp views.

Cost-aware by design:
- ONE BigQuery query per run, projecting only 5 narrow numeric columns
  (clickup_project, spend, revenue, orders, dt). creative_dashboard is columnar,
  so this scans ~65 MB (~$0.0004), NOT the full 14 GB. NEVER add SELECT * or the
  text columns (script / ai_remaining_transcript) — those are what make BQ pricey.
- Scope = tasks active in the last 30 days (spend_30d > 0) that live on the
  Creative Strategist list. Dormant tasks' lifetime numbers don't change, and the
  ClickUp side is a per-task loop (no bulk field endpoint), so we keep it small.

Env:
    GOOGLE_APPLICATION_CREDENTIALS  BQ service account json (for the `bq` CLI)
    TOKEN_FILE                      ClickUp pk token file (default ~/.config/clickup/pk)
    PERF_DRY_RUN=1                  compute + print targets, write nothing

Usage:
    PERF_DRY_RUN=1 python3 bq_to_clickup_perf.py     # preview
    python3 bq_to_clickup_perf.py                    # live write
"""
import http.client
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BQ_PROJECT = "ejam-dwh"
TABLE = "ejam-dwh.production.creative_dashboard"
LIST_ID = "901110066469"
TEAM_ID = "9011638245"
BASE = "https://api.clickup.com/api/v2"
TOKEN_FILE = os.path.expanduser(os.environ.get("TOKEN_FILE", "/tmp/clickup_pk"))
DRY_RUN = os.environ.get("PERF_DRY_RUN") == "1"
REQUEST_TIMEOUT = 60
MAX_WORKERS = 5

# field_id -> (row key, kind)  kind: "num" or "date_ms"
FIELDS = {
    "372c4db4-4e99-4f6a-b2c6-da27cc178182": ("roas_life", "num"),    # ROAS
    "c89e179f-ffe3-4374-85d4-a583b24402d1": ("spend_life", "num"),   # Spend
    "113fce5b-162d-4435-aaba-664910acf19a": ("orders_life", "num"),  # Orders
    "f232c84e-7afa-415d-9f70-22520495ce2c": ("spend_30d", "num"),    # Spend 30d
    "84b1b22b-9f72-4c3d-be98-b3ccbbdc3f11": ("last_active_ms", "date_ms"),  # Last Active
}

TOKEN = open(TOKEN_FILE).read().strip()

# narrow column projection only — keep this query cheap
BQ_SQL = """
SELECT
  clickup_project,
  ROUND(SUM(spend), 2) AS spend_life,
  ROUND(SAFE_DIVIDE(SUM(revenue), NULLIF(SUM(spend), 0)), 2) AS roas_life,
  CAST(ROUND(SUM(orders)) AS INT64) AS orders_life,
  ROUND(SUM(IF(dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY), spend, 0)), 2) AS spend_30d,
  CAST(UNIX_MILLIS(TIMESTAMP(MAX(dt))) AS INT64) AS last_active_ms
FROM `%s`
WHERE clickup_project LIKE 'SH-%%'
GROUP BY clickup_project
HAVING spend_30d > 0
""" % TABLE


def bq_rows():
    out = subprocess.run(
        ["bq", f"--project_id={BQ_PROJECT}", "query", "--use_legacy_sql=false",
         "--format=json", "--max_rows=100000", BQ_SQL],
        capture_output=True, text=True,
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


def list_custom_ids():
    """Every parent custom_id on the Creative Strategist list."""
    ids = set()
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
                ids.add(t["custom_id"])
        if len(batch) < 100:
            break
        page += 1
    return ids


def set_field(custom_id, field_id, value):
    api("POST", f"/task/{custom_id}/field/{field_id}",
        params={"custom_task_ids": "true", "team_id": TEAM_ID},
        body={"value": value})


def write_task(row):
    cid = row["clickup_project"]
    for field_id, (key, kind) in FIELDS.items():
        raw = row.get(key)
        if raw is None or raw == "":
            continue
        value = int(raw) if kind == "date_ms" else float(raw)
        set_field(cid, field_id, value)
    return cid


def main():
    print(f"{'DRY RUN — ' if DRY_RUN else ''}BQ -> ClickUp performance writeback")
    on_list = list_custom_ids()
    print(f"List {LIST_ID}: {len(on_list)} task custom_ids")

    rows = bq_rows()
    print(f"BQ active projects (spend_30d>0): {len(rows)}")

    targets = [r for r in rows if r["clickup_project"] in on_list]
    print(f"Targets (active AND on list): {len(targets)}")

    sample = sorted(targets, key=lambda r: float(r["spend_30d"]), reverse=True)[:8]
    print("\nTop 8 by 30d spend (what would be written):")
    for r in sample:
        print(f"  {r['clickup_project']}: ROAS {r['roas_life']} | Spend ${r['spend_life']} "
              f"| Orders {r['orders_life']} | 30d ${r['spend_30d']}")

    if DRY_RUN:
        print(f"\nDRY RUN: would write 5 fields to {len(targets)} tasks "
              f"({len(targets) * 5} field writes). No changes made.")
        return

    ok, errs = 0, []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futs = {pool.submit(write_task, r): r["clickup_project"] for r in targets}
        for fut in as_completed(futs):
            cid = futs[fut]
            try:
                fut.result()
                ok += 1
            except Exception as e:
                errs.append((cid, str(e)))
            if (ok + len(errs)) % 50 == 0:
                print(f"  {ok + len(errs)}/{len(targets)} done", flush=True)

    print(f"\nDone. {ok} tasks updated, {len(errs)} errors.")
    for cid, e in errs[:10]:
        print(f"  ERR {cid}: {e}")


if __name__ == "__main__":
    main()
