#!/usr/bin/env python3
"""
Creative fatigue sentinel — flag WINNING ads whose performance is decaying.

One BigQuery query per run against ejam-dwh.production.creative_dashboard at
ad_id x day grain, folded into two windows in-query (cheap columnar scan of
narrow numeric columns only — NEVER add the text columns script /
ai_remaining_transcript):

  now      = last NOW_WINDOW_DAYS days  (default 2 => "last 48h")
  baseline = the BASELINE_WINDOW_DAYS days immediately before that window
             (the 48h is excluded from the baseline)

Per active ad we compute, in each window:
  hook rate = view_3s_count / impressions
  hold      = video_p100_count / video_play_count   (video only)
  roas      = revenue / spend

Alert = a WINNER decaying:
  baseline roas above breakeven
  AND hook rate down > HOOK_DROP_REL relative  OR  roas down > ROAS_DROP_REL relative
  AND >= MIN_IMPRESSIONS_48H impressions in the now window (noise floor)

Output: ONE ntfy push (Priority high) listing the top TOP_N decaying ads by
now-window spend. No decaying winner => no push. Every Monday, a Priority min
heartbeat ("sentinel alive, N ads watched") regardless.

--dry-run : print the would-be push(es) instead of sending, EXCEPT send one
            real Priority min push tagged [TEST] so delivery is proven.

Env:
  GOOGLE_APPLICATION_CREDENTIALS  BQ service account json (for the `bq` CLI)
  NTFY_TOPIC                      ntfy topic (default tomas-tab-958e4431)
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import urllib.request

# ---- config (tune here) ---------------------------------------------------
FLOOR_SPEND_PER_DAY = 50.0     # active set: >= this * NOW_WINDOW_DAYS spend in the now window
NOW_WINDOW_DAYS = 2            # "last 48h"
BASELINE_WINDOW_DAYS = 7       # trailing baseline, excludes the now window
MIN_IMPRESSIONS_48H = 10000    # noise floor on the now window
HOOK_DROP_REL = 0.20           # hook rate down > 20% relative
ROAS_DROP_REL = 0.30           # roas down > 30% relative
BREAKEVEN_ROAS = 1.0           # baseline roas must be above this (a "winner")
TOP_N = 5                      # ads listed in the alert
BRAND = None                   # None = all brands; else exact brand string (creative_dashboard.brand)
# ---------------------------------------------------------------------------

BQ_PROJECT = "ejam-dwh"
TABLE = "ejam-dwh.production.creative_dashboard"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "tomas-tab-958e4431")
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

NOW_CUT = NOW_WINDOW_DAYS - 1                       # dt >= CURRENT_DATE - NOW_CUT  => NOW_WINDOW_DAYS days
BASE_START = NOW_CUT + BASELINE_WINDOW_DAYS         # full scan range
FLOOR_NOW = FLOOR_SPEND_PER_DAY * NOW_WINDOW_DAYS   # spend floor over the whole now window

BRAND_FILTER = ""
if BRAND:
    # BRAND is a hardcoded constant, not external input; escape quotes defensively.
    BRAND_FILTER = "AND brand = '%s'" % BRAND.replace("'", "")

BQ_SQL = """
SELECT
  ad_id,
  MAX(ad_name) AS ad_name,
  REGEXP_EXTRACT(MAX(ad_name), r"(SH-\\d+(?:-\\d+)+)") AS code,
  SUM(IF(dt >= DATE_SUB(CURRENT_DATE(), INTERVAL {now_cut} DAY), spend, 0))            AS spend_now,
  SUM(IF(dt >= DATE_SUB(CURRENT_DATE(), INTERVAL {now_cut} DAY), revenue, 0))          AS revenue_now,
  SUM(IF(dt >= DATE_SUB(CURRENT_DATE(), INTERVAL {now_cut} DAY), impressions, 0))      AS impr_now,
  SUM(IF(dt >= DATE_SUB(CURRENT_DATE(), INTERVAL {now_cut} DAY), view_3s_count, 0))    AS v3s_now,
  SUM(IF(dt >= DATE_SUB(CURRENT_DATE(), INTERVAL {now_cut} DAY), video_p100_count, 0)) AS vp100_now,
  SUM(IF(dt >= DATE_SUB(CURRENT_DATE(), INTERVAL {now_cut} DAY), video_play_count, 0)) AS vplay_now,
  SUM(IF(dt <  DATE_SUB(CURRENT_DATE(), INTERVAL {now_cut} DAY), spend, 0))            AS spend_base,
  SUM(IF(dt <  DATE_SUB(CURRENT_DATE(), INTERVAL {now_cut} DAY), revenue, 0))          AS revenue_base,
  SUM(IF(dt <  DATE_SUB(CURRENT_DATE(), INTERVAL {now_cut} DAY), impressions, 0))      AS impr_base,
  SUM(IF(dt <  DATE_SUB(CURRENT_DATE(), INTERVAL {now_cut} DAY), view_3s_count, 0))    AS v3s_base,
  SUM(IF(dt <  DATE_SUB(CURRENT_DATE(), INTERVAL {now_cut} DAY), video_p100_count, 0)) AS vp100_base,
  SUM(IF(dt <  DATE_SUB(CURRENT_DATE(), INTERVAL {now_cut} DAY), video_play_count, 0)) AS vplay_base
FROM `{table}`
WHERE dt >= DATE_SUB(CURRENT_DATE(), INTERVAL {base_start} DAY)
  {brand_filter}
GROUP BY ad_id
HAVING spend_now >= {floor_now}
""".format(
    now_cut=NOW_CUT, base_start=BASE_START, table=TABLE,
    brand_filter=BRAND_FILTER, floor_now=FLOOR_NOW,
)


def bq_rows():
    out = subprocess.run(
        ["bq", f"--project_id={BQ_PROJECT}", "query", "--use_legacy_sql=false",
         "--format=json", "--max_rows=100000", BQ_SQL],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise RuntimeError(f"bq query failed:\n{out.stderr}")
    return json.loads(out.stdout or "[]")


def f(row, key):
    v = row.get(key)
    return float(v) if v not in (None, "") else 0.0


def ratio(num, den):
    return num / den if den > 0 else None


def rel_drop(base, now):
    """Relative decline from base to now; None if base is not a usable positive."""
    if base is None or now is None or base <= 0:
        return None
    return (base - now) / base


def evaluate(row):
    """Return an alert dict if this active ad is a decaying winner, else None."""
    spend_now = f(row, "spend_now")
    impr_now = f(row, "impr_now")

    roas_base = ratio(f(row, "revenue_base"), f(row, "spend_base"))
    roas_now = ratio(f(row, "revenue_now"), spend_now)
    hook_base = ratio(f(row, "v3s_base"), f(row, "impr_base"))
    hook_now = ratio(f(row, "v3s_now"), impr_now)
    hold_base = ratio(f(row, "vp100_base"), f(row, "vplay_base"))
    hold_now = ratio(f(row, "vp100_now"), f(row, "vplay_now"))

    # winner gate + noise floor
    if roas_base is None or roas_base <= BREAKEVEN_ROAS:
        return None
    if impr_now < MIN_IMPRESSIONS_48H:
        return None

    hook_d = rel_drop(hook_base, hook_now)
    roas_d = rel_drop(roas_base, roas_now)
    decaying = (hook_d is not None and hook_d > HOOK_DROP_REL) or \
               (roas_d is not None and roas_d > ROAS_DROP_REL)
    if not decaying:
        return None

    code = (row.get("code") or "").strip() or row.get("ad_id") or "?"
    return {
        "code": code, "spend_now": spend_now,
        "roas_now": roas_now, "roas_base": roas_base,
        "hook_now": hook_now, "hook_base": hook_base,
        "hold_now": hold_now, "hold_base": hold_base,
        "hook_drop": hook_d, "roas_drop": roas_d,
    }


def fmt_pct(x):
    return f"{x * 100:.1f}%" if x is not None else "n/a"


def fmt_roas(x):
    return f"{x:.2f}" if x is not None else "n/a"


def alert_line(a):
    return (f"{a['code']} | ${a['spend_now']:.0f} | "
            f"roas {fmt_roas(a['roas_base'])}->{fmt_roas(a['roas_now'])} | "
            f"hook {fmt_pct(a['hook_base'])}->{fmt_pct(a['hook_now'])}")


def send_ntfy(title, body, priority):
    req = urllib.request.Request(
        NTFY_URL, data=body.encode(), method="POST",
        headers={"Title": title, "Priority": priority},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        resp.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="print would-be pushes; send only a [TEST] Priority min push")
    args = ap.parse_args()

    rows = bq_rows()
    watched = len(rows)
    print(f"{'DRY RUN — ' if args.dry_run else ''}fatigue sentinel: {watched} active ads "
          f"(spend_now >= ${FLOOR_NOW:.0f})")

    alerts = [a for a in (evaluate(r) for r in rows) if a]
    alerts.sort(key=lambda a: a["spend_now"], reverse=True)
    top = alerts[:TOP_N]

    is_monday = datetime.date.today().weekday() == 0

    if top:
        title = f"Creative fatigue: {len(alerts)} winner(s) decaying"
        body = "\n".join(alert_line(a) for a in top)
        if args.dry_run:
            print(f"\n[WOULD PUSH — Priority high] {title}\n{body}")
        else:
            send_ntfy(title, body, "high")
            print(f"pushed alert: {len(top)} ad(s)")
    else:
        print("no decaying winners — no alert push")

    if is_monday:
        hb = f"sentinel alive, {watched} ads watched"
        if args.dry_run:
            print(f"\n[WOULD PUSH — Priority min, Monday heartbeat] {hb}")
        else:
            send_ntfy("Fatigue sentinel heartbeat", hb, "min")
            print(f"pushed heartbeat: {hb}")
    else:
        print(f"not Monday ({datetime.date.today():%A}) — no heartbeat")

    if args.dry_run:
        # Prove delivery end-to-end without spamming a real alert.
        send_ntfy("[TEST] Fatigue sentinel",
                  f"dry-run delivery check — {watched} ads watched, "
                  f"{len(alerts)} decaying winner(s)", "min")
        print("\nsent one real [TEST] Priority min push (delivery proof)")


if __name__ == "__main__":
    main()
