# BigQuery → ClickUp performance writeback

Stamps ad performance from the BigQuery creative dashboard onto ClickUp tasks so
performance is **sortable and filterable** in ClickUp views (the existing ETL bot
posts the same data as comments, which you can't filter on). Runs **daily 07:30
local** via launchd.

## What it writes

For every task on the Creative Strategist list (`901110066469`) that was **active
in the last 30 days** (had ad spend), it sets 5 custom fields from
`ejam-dwh.production.creative_dashboard`, matched on `clickup_project` = SH-####:

| ClickUp field | Source |
|---|---|
| ROAS (number) | lifetime revenue / spend |
| Spend (number) | lifetime spend |
| Orders (number) | lifetime orders |
| Spend 30d (number) | spend in last 30 days |
| Last Active (date) | most recent active date |

Scope is active-in-30d because dormant tasks' lifetime numbers don't change and
the ClickUp side is a per-task loop (no bulk field endpoint). First run touched
~119 tasks.

## Cost

ONE BigQuery query per run, projecting only 5 narrow numeric columns. Because the
table is columnar, this scans ~65 MB (~$0.0004/run, ~$0.15/yr daily) — NOT the
14 GB table. **Do not add `SELECT *` or the text columns (`script`,
`ai_remaining_transcript`) — those are what make this table expensive.** The table
is partitioned on `asset_published_at`, not `dt`, so date filters don't prune;
column selection is what keeps it cheap.

## One-time setup (per Mac)

Reuses the same creds as the other crons:
- BQ service account at `~/.config/gcloud/ejam-dwh-sa.json` (`GOOGLE_APPLICATION_CREDENTIALS`)
- ClickUp token at `~/.config/clickup/pk`
- `bq` CLI on PATH

The 5 custom fields must exist on the list (created in the ClickUp UI). Field IDs
are hard-coded in `bq_to_clickup_perf.py`; if the fields are recreated, re-fetch
IDs (`curl -H "Authorization: $(cat ~/.config/clickup/pk)" https://api.clickup.com/api/v2/list/901110066469/field`)
and update the `FIELDS` map.

Install the job:

```sh
cp "$HOME/Library/CloudStorage/GoogleDrive-propeidzas@gmail.com/My Drive/Code Things/systems/bq-clickup-perf/com.tomas.bq-clickup-perf.plist" "$HOME/Library/LaunchAgents/"
launchctl unload "$HOME/Library/LaunchAgents/com.tomas.bq-clickup-perf.plist" 2>/dev/null
launchctl load "$HOME/Library/LaunchAgents/com.tomas.bq-clickup-perf.plist"
```

## Run manually / preview

```sh
# preview only (writes nothing):
PERF_DRY_RUN=1 GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/ejam-dwh-sa.json TOKEN_FILE=~/.config/clickup/pk \
  python3 "$HOME/Library/CloudStorage/GoogleDrive-propeidzas@gmail.com/My Drive/Code Things/systems/bq-clickup-perf/bq_to_clickup_perf.py"

# live (or trigger the launchd job):
bash "$HOME/Library/CloudStorage/GoogleDrive-propeidzas@gmail.com/My Drive/Code Things/systems/bq-clickup-perf/run_perf_writeback.sh"
launchctl start com.tomas.bq-clickup-perf
tail -n 30 "$HOME/Library/Logs/bq-clickup-perf/"*.log
```

## Notes

- Per-Mac: plist, creds, and `~/Library/Logs/` are local; scripts ride Drive.
- ROAS is first-purchase (revenue/spend from the dashboard); sub LTV runs higher.
- Schedule: daily 07:30, ahead of the Monday 08:00 winners refresh + 09:07 report.
