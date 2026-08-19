#!/bin/bash
# SHA combination-suggestion report. Usage: run.sh [END_DATE]  (default: yesterday)
set -euo pipefail
[ -f ~/.config/gcloud/ejam-dwh-sa.json ] || { echo "FATAL: BQ SA key missing" >&2; exit 1; }
exec python3 "$(dirname "$0")/report.py" "$@"
