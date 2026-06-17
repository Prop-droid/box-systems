#!/bin/bash
# Redeploy cron scripts from their canonical home (Code Things/systems on Drive)
# to local ~/sha-systems. launchd cannot exec scripts on Google Drive (TCC),
# so plists point here; edit the Drive copies, then run this.
set -euo pipefail
D="/home/tomas/brain/systems"
L="$HOME/sha-systems"

cp "$D/winners-refresh/run_winners_refresh.sh" "$L/winners-refresh/"
cp -R "$D/sha-weekly-report/run_report.sh" "$D/sha-weekly-report/report_prompt.txt" "$D/sha-weekly-report/queries" "$L/sha-weekly-report/"
cp -R "$D/research-agent/bin" "$D/research-agent/prompts" "$D/research-agent/monitor.conf" "$L/research-agent/"
chmod +x "$L"/winners-refresh/*.sh "$L"/sha-weekly-report/*.sh "$L"/research-agent/bin/*.sh
echo "deployed: winners-refresh, sha-weekly-report, research-agent"
# bq-clickup-perf already lives locally in $L/bq-clickup-perf (canonical there).
# watchdog is canonical in $L/watchdog.
