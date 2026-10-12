# BigQuery → ClickUp performance writeback

Stamps **Meta** ad performance onto ClickUp tasks so it is **sortable and
filterable** in ClickUp views (the ETL bot's comments aren't filterable). Runs
**daily 14:30 Vilnius** via `systemd/bq-clickup-perf.timer`, after the US ad
day has closed and facebook_dashboard has rebuilt (~11:00 UTC).

## What it writes

Every task on the Creative Strategist list (`901110066469`) with Meta spend gets
5 custom fields, from `ejam-dwh.production.facebook_dashboard`
(`brand='SHA'`, `type='placement_breakdown'`):

| ClickUp field | Source |
|---|---|
| ROAS (number) | lifetime last-click revenue / spend (internal, not Meta pixel ROAS) |
| Spend (number) | lifetime Meta spend |
| Orders (number) | lifetime last-click orders |
| Spend 30d (number) | Meta spend over the last 30 complete days (0 once quiet) |
| Last Active (date) | last day with spend > 0 |

Task key per ad = `creative_dashboard.clickup_project` when CAMS maps the ad,
else the first `SH-####` in the ad name. Only changed fields are written; tasks
with no Meta spend but leftover values get cleared. The script aborts before
writing if BQ returns < 1000 projects (protects against mass clearing).

Meta only by decision (2026-10-12): AppLovin/TikTok spend is NOT in these fields.

## Why facebook_dashboard, not creative_dashboard

Audit 2026-10-12 (`~/brain/projects/2026-10/clickup-perf-audit/AUDIT.md`):
creative_dashboard drops Meta ads with no CAMS asset record (~$172k SHA spend
Jun–Oct 2026; SH-17273 showed $22.7k vs $118.6k). Matched ads agree to the cent.

## Cost

Lifetime aggregate over facebook_dashboard ≈ 8 GB scanned (~$0.05/run). Keep the
projection narrow; `ad_name` is the expensive column. Never `SELECT *`.

## Run manually

```sh
# preview (writes nothing):
PERF_DRY_RUN=1 GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/ejam-dwh-sa.json \
  python3 ~/systems/bq-clickup-perf/bq_to_clickup_perf.py

# live:
systemctl --user start bq-clickup-perf.service
tail -n 30 "$(ls -td ~/Library/Logs/bq-clickup-perf/* | head -1)"
```

Field IDs are hard-coded in `FIELDS`; if the fields are recreated, re-fetch via
`curl -H "Authorization: $(cat ~/.config/clickup/pk)" https://api.clickup.com/api/v2/list/901110066469/field`.

Fields are display columns in the list views "WL View", "Open WL SHA" and
"CS View" (no view sorts/filters on them as of 2026-10-12).
