#!/bin/bash
# Usage: run.sh [FROM] [TO]  (defaults: last 28 days)
export GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/ejam-dwh-sa.json
FROM=${1:-$(date -d '28 days ago' +%F)}; TO=${2:-$(date -d 'yesterday' +%F)}
sed "s/@from/$FROM/; s/@to/$TO/" "$(dirname "$0")/attention_metrics.sql" | bq query --use_legacy_sql=false --format=pretty --quiet
