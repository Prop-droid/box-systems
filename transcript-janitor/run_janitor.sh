#!/bin/bash
# Transcript janitor: gzip + archive Claude Code session transcripts older than 30 days.
# Never deletes; never touches memory/ dirs (*.md) — only *.jsonl session files.
set -uo pipefail

SRC="$HOME/.claude/projects"
DST="$HOME/.claude/archive/projects"
DAYS=30

before=$(du -sm "$SRC" | awk '{print $1}')
count=0
while IFS= read -r f; do
  rel="${f#"$SRC"/}"
  mkdir -p "$DST/$(dirname "$rel")"
  gzip -c "$f" > "$DST/$rel.gz" && rm "$f"
  count=$((count+1))
done < <(find "$SRC" -name '*.jsonl' -mtime +$DAYS -not -path '*/memory/*' 2>/dev/null)
after=$(du -sm "$SRC" | awk '{print $1}')

echo "janitor: archived $count transcripts (>${DAYS}d), ${before}M -> ${after}M"
