#!/bin/bash
# recall.sh <skill> [n]
# Prints a compact "Past lessons" block for the given skill, ready to inject
# into a headless `claude -p` prompt (this is the Reflexion priming step).
# Pulls gbrain pages tagged skill:<skill>, most recent first, and extracts the
# Lesson / How-to-apply lines. Prints nothing if there are no lessons yet.
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$DIR/env.sh"

SKILL="${1:-}"
N="${2:-5}"
[ -n "$SKILL" ] || { echo "usage: recall.sh <skill> [n]" >&2; exit 2; }
command -v gbrain >/dev/null || { echo "" ; exit 0; }

# Use the base tag (reliably indexed) + slug-prefix filter for this skill.
# The `--type` and colon-tag indexes lag on just-written pages; the base tag
# does not. slug \t type \t date \t title -> sort by date desc, take N.
mapfile -t SLUGS < <(gbrain list --tag task-lesson -n 1000 2>/dev/null \
  | grep "^${SLUG_PREFIX:-lessons}/${SKILL}/" \
  | sort -t$'\t' -k3,3r | head -n "$N" | cut -f1)

[ "${#SLUGS[@]}" -gt 0 ] || exit 0

echo "Past lessons for ${SKILL} (most recent ${#SLUGS[@]}):"
for slug in "${SLUGS[@]}"; do
  [ -n "$slug" ] || continue
  page="$(gbrain get "$slug" 2>/dev/null)" || continue
  lesson="$(printf '%s\n' "$page"  | grep -m1 '^\*\*Lesson:\*\*'        | sed 's/^\*\*Lesson:\*\* *//')"
  how="$(printf '%s\n' "$page"     | grep -m1 '^\*\*How to apply:\*\*'  | sed 's/^\*\*How to apply:\*\* *//')"
  what="$(printf '%s\n' "$page"    | grep -m1 '^\*\*What happened:\*\*' | sed 's/^\*\*What happened:\*\* *//')"
  body="${lesson:-$what}"
  [ -n "$body" ] || continue
  if [ -n "$how" ]; then
    echo "- ${body} (apply: ${how})"
  else
    echo "- ${body}"
  fi
done
