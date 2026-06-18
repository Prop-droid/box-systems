# SHA Weekly Brand-Health Report

Automated weekly Shameless Snacks paid-acquisition report. Pulls from `ejam-dwh.production.creative_dashboard`, compares last week vs prior week vs 4-week rolling avg, then has Claude CLI generate the markdown report with tactical + strategic recommendations.

## How it runs

- **Trigger:** local launchd plist at `~/Library/LaunchAgents/com.tomas.sha-weekly-report.plist`
- **Schedule:** Monday at 09:07 Europe/Vilnius (local Mac time)
- **Catches up if Mac was asleep at the fire time** (launchd `StartCalendarInterval` semantics)
- **Output:** `Code Things/projects/YYYY-MM/sha-weekly-report-<YYYY-MM-DD>/report.md` (where `<YYYY-MM-DD>` = Monday of the reported week)

## Files in this system

```
sha-weekly-report/
├── README.md                  -- you are here
├── run_report.sh              -- orchestrator (bq queries → assemble → claude → report.md)
├── report_prompt.txt          -- prompt template fed to claude CLI
└── queries/
    ├── 01_topline.sql         -- last wk vs prior wk vs 4-wk avg baseline
    ├── 02_channels.sql        -- channel breakdown
    ├── 03_top_spend.sql       -- top 15 spenders
    ├── 04_top_roas.sql        -- top 10 ROAS (min $500 spend)
    ├── 05_losers.sql          -- top 10 losers ($1K+ spend, <0.5 ROAS)
    └── 06_angles.sql          -- AI angle breakdown
```

## Per-week output

```
Code Things/projects/2026-06/sha-weekly-report/2026-05-25/
├── report.md             -- final report (the thing to read)
├── 01_topline.txt        -- raw bq output
├── 02_channels.txt
├── 03_top_spend.txt
├── 04_top_roas.txt
├── 05_losers.txt
├── 06_angles.txt
├── _assembled_prompt.txt -- exact prompt sent to claude (debug)
├── _run.log              -- script execution log
└── _claude.err           -- claude stderr (only present on failure)
```

## Manual run

```bash
cd "Code Things/systems/sha-weekly-report"
bash run_report.sh                  # auto-detect last Mon→Sun
bash run_report.sh 2026-05-25       # explicit Monday-of-week
```

## Dependencies

- `bq` CLI (`brew install google-cloud-sdk`) authed against `ejam-dwh-sa.json`
- `claude` CLI authed (Tomas's login)
- `python3` (used for date math; ships with macOS)
- Env vars in `~/.hermes/.env`: `EJAM_BQ_PROJECT`, `EJAM_BQ_DATASET`, `GOOGLE_APPLICATION_CREDENTIALS`

## Cross-machine note

- Script and queries live in Drive — sync automatically.
- The launchd plist (per-Mac, absolute paths) does NOT live in Drive. See `docs/setup-mac.md` for the install steps on a fresh Mac. Windows install is not supported (would need Task Scheduler).
