#!/usr/bin/env bash
IN=$(cat)
BASE=$(printf "%s" "$IN" | bash ~/.claude/statusline-command.sh 2>/dev/null)
S="$HOME/.claude/usage-window.json"
SEG=""
if [ -f "$S" ]; then
  AGE=$(( $(date +%s) - $(stat -c %Y "$S" 2>/dev/null) ))
  if [ "$AGE" -le 1200 ]; then
    PCT=$(python3 -c "import json;print(json.load(open(\"$S\"))[\"pct\"])" 2>/dev/null)
    if [ -n "$PCT" ]; then
      if [ "$PCT" -ge 90 ]; then SEG=" · ⚠ 5h window ${PCT}% USED — last 10% reserved"
      else SEG=" · 5h:${PCT}%"; fi
    fi
  fi
fi
printf "%s%s" "$BASE" "$SEG"
