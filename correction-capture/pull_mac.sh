#!/bin/bash
# Pull recent Claude transcripts from the Mac (Tailscale) into staging/mac/.
# Best-effort: the Mac sleeps; a failed pull must not fail the pipeline.
set -uo pipefail
DIR="$HOME/systems/correction-capture"
MAC="tomas@100.68.166.21"
KEY="$HOME/.ssh/id_ed25519_mac"
SSH_OPTS=(-i "$KEY" -o ConnectTimeout=10 -o BatchMode=yes -o StrictHostKeyChecking=accept-new)

LIST="$(mktemp)"
trap 'rm -f "$LIST"' EXIT
if ! ssh "${SSH_OPTS[@]}" "$MAC" \
    'cd ~/.claude/projects && find . -name "*.jsonl" -type f -mtime -30 ! -path "*/memory/*"' \
    > "$LIST" 2>/dev/null; then
  echo "pull_mac: Mac unreachable, skipping (box-only scan this run)"
  exit 0
fi
rsync -az --timeout=120 --files-from="$LIST" \
  -e "ssh ${SSH_OPTS[*]}" \
  "$MAC:.claude/projects/" "$DIR/staging/mac/" \
  && echo "pull_mac: synced $(wc -l < "$LIST" | tr -d ' ') file(s)" \
  || echo "pull_mac: rsync failed, continuing with whatever is staged"
exit 0
