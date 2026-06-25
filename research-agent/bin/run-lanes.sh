#!/usr/bin/env bash
set -euo pipefail
set -a; . "$HOME/.hermes/.env"; set +a
export ATRIA_DIR="$HOME/brain/projects/2026-06/competitor-ads-scrape/atria"
export LANES_CANON="$HOME/brain/systems/research-agent/lanes/canon.json"
export LANES_OUT="$HOME/brain/systems/research-agent/output/lanes"
export COMMENTS_DIGEST_DIR="$HOME/systems/comments-digest/out"
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/ejam-dwh-sa.json"
export BQ_TABLE="$(grep '^BQ_TABLE=' "$HOME/creative-command-center/.env.local" | cut -d= -f2)"
export BRAND="$(grep '^BRAND=' "$HOME/creative-command-center/.env.local" | cut -d= -f2)"
exec node "$HOME/systems/research-agent/lanes/build-lanes.mjs" "$@"
