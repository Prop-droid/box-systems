#!/usr/bin/env python3
"""
Format lifecycle report: classify each video format (from ai.asset_tagging_video
format_style tags) as FRESH / SCALING / PEAKING / FATIGUING using our own weekly
spend + ROAS curves, instead of eyeballing the Ad Library.

Join: creative_dashboard asset_link "video_id=<id>" -> asset_tagging_video.asset_id
(verified 100% of SHA July video spend joins). Statics are NOT covered: the
static tagging table keys on an md5 file hash with no counterpart column in
creative_dashboard — needs a join key from the data team.

Usage:
    python3 format_lifecycle.py            # SHA, last 8 ISO weeks
    python3 format_lifecycle.py --weeks 12
    python3 format_lifecycle.py --brand SHA --min-spend 2000

Output: markdown report to reports/format-lifecycle-<date>.md (+ stdout summary).
Needs BQ SA at ~/.config/gcloud/ejam-dwh-sa.json and `bq` on PATH.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
SA = os.path.expanduser("~/.config/gcloud/ejam-dwh-sa.json")

QUERY = """
WITH vid AS (
  SELECT
    REGEXP_EXTRACT(asset_link, r'video_id=(\\d+)') vid,
    DATE_TRUNC(dt, WEEK(MONDAY)) wk,
    SUM(spend) spend, SUM(revenue) revenue, SUM(orders) orders
  FROM `ejam-dwh.production.creative_dashboard`
  WHERE brand = '{brand}' AND dt >= '{start}' AND dt < '{end}'
    AND asset_type = 'VIDEO' AND spend > 0
  GROUP BY 1, 2
)
SELECT t.format_style, CAST(v.wk AS STRING) wk,
  ROUND(SUM(v.spend), 2) spend, ROUND(SUM(v.revenue), 2) revenue,
  SUM(v.orders) orders, COUNT(DISTINCT v.vid) assets
FROM vid v
JOIN `ejam-dwh.ai.asset_tagging_video` t ON v.vid = t.asset_id
WHERE t.format_style IS NOT NULL AND t.format_style != ''
GROUP BY 1, 2
"""


def bq(sql):
    env = dict(os.environ, GOOGLE_APPLICATION_CREDENTIALS=SA)
    r = subprocess.run(
        ["bq", "query", "--project_id=ejam-dwh", "--use_legacy_sql=false",
         "--format=json", "--max_rows=100000"],
        input=sql, capture_output=True, text=True, env=env, timeout=300)
    if r.returncode != 0:
        sys.exit(f"bq failed:\n{r.stderr[-2000:]}")
    return json.loads(r.stdout or "[]")


def classify(weeks, series, total_weeks):
    """series: {wk_index: {'spend':..,'revenue':..}} over 0..total_weeks-1."""
    def avg(field, idxs):
        vals = [series.get(i, {}).get(field, 0.0) for i in idxs]
        return sum(vals) / max(len(idxs), 1)

    last2 = [total_weeks - 2, total_weeks - 1]
    prior2 = [total_weeks - 4, total_weeks - 3]
    recent_spend, prior_spend = avg("spend", last2), avg("spend", prior2)
    recent_rev, prior_rev = avg("revenue", last2), avg("revenue", prior2)
    recent_roas = recent_rev / recent_spend if recent_spend else 0
    prior_roas = prior_rev / prior_spend if prior_spend else 0

    first_seen = min(series)
    is_new = first_seen >= total_weeks - 4
    trend = recent_spend / prior_spend if prior_spend else float("inf")
    roas_trend = recent_roas / prior_roas if prior_roas else 1.0

    spent_before_recent = any(
        series.get(i, {}).get("spend", 0) > 50 for i in range(total_weeks - 2))
    if recent_spend < 50 and spent_before_recent:
        phase = "DEAD"
    elif is_new and (prior_spend == 0 or trend > 1.0):
        phase = "FRESH"
    elif trend > 1.3 and roas_trend >= 0.85:
        phase = "SCALING"
    elif trend < 0.6 or roas_trend < 0.7:
        phase = "FATIGUING"
    else:
        phase = "PEAKING"
    return phase, recent_spend, recent_roas, trend, roas_trend


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", default="SHA")
    ap.add_argument("--weeks", type=int, default=8)
    ap.add_argument("--min-spend", type=float, default=2000,
                    help="min total spend over the window to include a format")
    args = ap.parse_args()

    end = date.today() - timedelta(days=date.today().weekday())  # this Monday
    start = end - timedelta(weeks=args.weeks)
    rows = bq(QUERY.format(brand=args.brand, start=start, end=end))

    week_index = {str(start + timedelta(weeks=i)): i for i in range(args.weeks)}
    formats = {}
    for r in rows:
        wk = r["wk"][:10]
        if wk not in week_index:
            continue
        f = formats.setdefault(r["format_style"], {"series": {}, "assets": 0})
        i = week_index[wk]
        cell = f["series"].setdefault(i, {"spend": 0.0, "revenue": 0.0})
        cell["spend"] += float(r["spend"])
        cell["revenue"] += float(r["revenue"])
        f["assets"] = max(f["assets"], int(r["assets"]))

    results = []
    for name, f in formats.items():
        total = sum(c["spend"] for c in f["series"].values())
        if total < args.min_spend:
            continue
        phase, rspend, rroas, trend, rtrend = classify(
            week_index, f["series"], args.weeks)
        results.append({
            "format": name, "phase": phase, "total_spend": total,
            "recent_wk_spend": rspend, "recent_roas": rroas,
            "spend_trend": trend, "roas_trend": rtrend, "assets": f["assets"],
        })

    order = {"FRESH": 0, "SCALING": 1, "PEAKING": 2, "FATIGUING": 3, "DEAD": 4}
    results.sort(key=lambda x: (order[x["phase"]], -x["total_spend"]))

    today = date.today().isoformat()
    lines = [
        f"# Format lifecycle — {args.brand} — {today}",
        "",
        f"Window: {start} → {end} ({args.weeks} ISO weeks), videos only "
        f"(statics lack a join key). Source: creative_dashboard × ai.asset_tagging_video "
        f"`format_style`. Formats under ${args.min_spend:,.0f} window spend excluded.",
        "",
        "Phases — FRESH: first spend in last 4 wks, growing. SCALING: spend up >1.3x "
        "wk-over-wk pairs, ROAS holding. PEAKING: plateau. FATIGUING: spend down >40% "
        "or ROAS down >30%. DEAD: spend collapsed to ~0. Ride FRESH/SCALING, refresh "
        "PEAKING, stop briefing FATIGUING.",
        "",
        "| Phase | Format | 8wk spend | last-wk avg | ROAS now | spend trend | ROAS trend | assets |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        tr = "new" if r["spend_trend"] == float("inf") else f"{r['spend_trend']:.2f}x"
        lines.append(
            f"| {r['phase']} | {r['format']} | ${r['total_spend']:,.0f} "
            f"| ${r['recent_wk_spend']:,.0f} | {r['recent_roas']:.2f} "
            f"| {tr} | {r['roas_trend']:.2f}x | {r['assets']} |")

    out_dir = HERE / "reports"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"format-lifecycle-{today}.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
